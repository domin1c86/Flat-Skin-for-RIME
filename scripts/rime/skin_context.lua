-- Local contextual ranking + next-word predictions. Native userdb is untouched.
-- Processor owns notifications and state; translator/filter only read it.
local M = {processor={}, translator={}, filter={}}
local states, databases, serial = {}, {}, 0
local marker = "›"
local chinese = {double_pinyin_flypy=true, rime_mint=true, rime_mint_flypy=true}

local function now() return os.time() end
local function letter(code)
  return (code >= 0x41 and code <= 0x5a) or (code >= 0x61 and code <= 0x7a)
end
local function han(text)
  if not text or text == "" or #text > 128 then return false end
  local ok, valid = pcall(function()
    for _, c in utf8.codes(text) do
      if not ((c >= 0x3400 and c <= 0x9fff) or (c >= 0x20000 and c <= 0x323af)) then return false end
    end
    return true
  end)
  return ok and valid
end

local function state(env)
  return states[env.engine.context:get_property("skin_context_id")]
end

local function active(env)
  local ctx = env.engine.context
  return chinese[env.engine.schema.schema_id] and not ctx:get_option("ascii_mode")
      and ctx:get_option("context_learning")
end

local function cancel(ctx, st)
  st.want_predict, st.predicting = false, false
  ctx:set_option("skin_context_prediction", false)
  if ctx.input == marker then ctx:clear() end
end

local function reset(ctx, st)
  cancel(ctx, st)
  st.previous, st.previous_time, st.undo = nil, nil, nil
end

local function fetch(st, key)
  if not st.db then return nil, false end
  local ok, value = pcall(function() return st.db:fetch(key) end)
  if not ok then return nil, false end
  return value, true
end

local function write(st, key, value)
  if not st.db then return false end
  local ok, result = pcall(function()
    if value == nil then return st.db:erase(key) end
    return st.db:update(key, value)
  end)
  return ok and result ~= false
end

local function decode(value)
  local rows = {}
  if type(value) ~= "string" or #value > 65536 then return rows end
  for word, count, timestamp in value:gmatch("([^\t\n]+)\t(%d+)\t(%d+)\n") do
    if han(word) and #rows < 20 then
      rows[#rows+1] = {text=word, count=tonumber(count), time=tonumber(timestamp)}
    end
  end
  return rows
end

local function ranked(st, previous, threshold)
  local rows, result = decode(fetch(st, previous)), {}
  table.sort(rows, function(a,b)
    if a.count == b.count then
      if a.time == b.time then return a.text < b.text end
      return a.time > b.time
    end
    return a.count > b.count
  end)
  for _, row in ipairs(rows) do
    if row.count >= threshold then result[#result+1] = row.text end
  end
  return result
end

local function remember(st, previous, word)
  local old, readable = fetch(st, previous)
  if not readable then return end
  local rows, found = decode(old), false
  for _, row in ipairs(rows) do
    if row.text == word then
      row.count, row.time, found = math.min(row.count+1, 1000000), now(), true
      break
    end
  end
  if not found then rows[#rows+1] = {text=word, count=1, time=now()} end
  table.sort(rows, function(a,b)
    if a.count == b.count then return a.time > b.time end
    return a.count > b.count
  end)
  local encoded = {}
  for i=1, math.min(#rows,20) do
    local row = rows[i]
    encoded[#encoded+1] = row.text .. "\t" .. row.count .. "\t" .. row.time .. "\n"
  end
  if write(st, previous, table.concat(encoded)) then
    st.undo = {key=previous, value=old, time=now()}
  end
end

local function preceding(st)
  if st.previous and now() - st.previous_time <= st.timeout then return st.previous end
  st.previous, st.previous_time = nil, nil
end

function M.processor.init(env)
  local ctx, config = env.engine.context, env.engine.schema.config
  serial = serial+1
  env.id = tostring(serial)
  local st = {timeout=config:get_int("skin_context/timeout_seconds") or 30,
              threshold=config:get_int("skin_context/min_count") or 2,
              limit=config:get_int("skin_context/max_predictions") or 5}
  st.timeout = math.max(1,math.min(st.timeout,300))
  st.threshold = math.max(1,st.threshold)
  st.limit = math.max(1,math.min(st.limit,5))
  env.db_key = rime_api.get_user_data_dir()
  local ok, db = pcall(function()
    if not chinese[env.engine.schema.schema_id] then return nil end
    local shared = databases[env.db_key]
    if shared then shared.users=shared.users+1; return shared.db end
    local result = LevelDb("skin_context")
    if result:open() then
      databases[env.db_key] = {db=result,users=1}
      return result
    end
  end)
  if ok then st.db = db end
  states[env.id] = st
  ctx:set_property("skin_context_id", env.id)
  ctx:set_option("skin_context_prediction", false)
  env.commit_connection = ctx.commit_notifier:connect(function(c)
    local text = c:get_commit_text()
    local predicted = st.predicting and c.input == marker
    st.want_predict, st.predicting, st.undo = false, false, nil
    c:set_option("skin_context_prediction", false)
    if not active(env) or not han(text) then reset(c,st); return end
    local previous = preceding(st)
    if previous then remember(st, previous, text) end
    st.previous, st.previous_time = text, now()
    if not predicted and c:get_option("prediction") then
      st.predictions = ranked(st, text, st.threshold)
      st.want_predict = #st.predictions > 0
    end
  end)
  env.update_connection = ctx.update_notifier:connect(function(c)
    if st.want_predict and c.input == "" and active(env) and c:get_option("prediction") then
      st.want_predict, st.predicting = false, true
      c:set_option("skin_context_prediction",true)
      c:push_input(marker)
    elseif st.predicting and c.input ~= marker then
      st.predicting = false
      c:set_option("skin_context_prediction",false)
    end
  end)
  env.option_connection = ctx.option_update_notifier:connect(function(c,name)
    if name == "context_learning" and not c:get_option(name) then reset(c,st)
    elseif name == "prediction" and not c:get_option(name) then cancel(c,st)
    elseif name == "ascii_mode" then reset(c,st) end
  end)
end

function M.processor.func(key, env)
  if key:release() then return 2 end
  local ctx, st = env.engine.context, state(env)
  if not st then return 2 end
  -- Two signals used around frontend actions that bypass the Rime engine.
  if key:ctrl() and key:shift() and not key:alt() and not key:super() then
    if key.keycode == 0xffc6 then cancel(ctx,st); return 1 end -- F9
    if key.keycode == 0xffc7 then reset(ctx,st); return 1 end  -- F10
  end
  if not active(env) then reset(ctx,st); return 2 end
  local repr = key:repr()
  local predicting = st.predicting and ctx.input == marker
  if predicting then
    if key.keycode == 0xff08 then cancel(ctx,st); return 1 end
    if key.keycode == 0x20 then
      reset(ctx,st); env.engine:commit_text(" "); return 1
    end
    if key.keycode == 0xff0d then cancel(ctx,st); reset(ctx,st); return 2 end
    -- Navigation/number selection is left to selector; letters start input.
    if repr == "Left" or repr == "Right" or repr == "Home" or repr == "End" then
      reset(ctx,st); return 2
    end
    if key.keycode >= 0x30 and key.keycode <= 0x39 then return 2 end
    if not key:ctrl() and not key:alt() and not key:super()
        and letter(key.keycode) then
      cancel(ctx,st)
      st.undo = nil
      return 2
    end
    if repr == "Up" or repr == "Down" or repr == "Page_Up" or repr == "Page_Down"
        or repr == "Shift_L" or repr == "Shift_R" then return 2 end
    reset(ctx,st)
    return 2
  end
  if key.keycode == 0xff08 and ctx.input == "" then
    if st.undo and now()-st.undo.time <= 3 then write(st,st.undo.key,st.undo.value) end
    reset(ctx,st)
    return 2
  end
  if repr == "Left" or repr == "Right" or repr == "Home" or repr == "End"
      or key.keycode == 0xff0d or (ctx.input == "" and key.keycode == 0x20) then
    reset(ctx,st)
  elseif ctx.input == "" and not key:ctrl() and not key:alt() and not key:super()
      and letter(key.keycode) then
    st.undo = nil
  end
  return 2
end

function M.processor.fini(env)
  for _, key in ipairs({'commit_connection','update_connection','option_connection'}) do
    if env[key] then env[key]:disconnect() end
  end
  local st = states[env.id]
  states[env.id] = nil
  local shared = st and st.db and databases[env.db_key]
  if shared then
    shared.users = shared.users-1
    if shared.users == 0 then
      databases[env.db_key] = nil
      pcall(function() shared.db:close() end)
    end
  end
end

function M.translator.func(input, seg, env)
  local st = state(env)
  if not st or input ~= marker or not st.predicting or not active(env)
      or not env.engine.context:get_option("prediction") then return end
  for i=1, math.min(#st.predictions,st.limit) do
    local cand = Candidate("skin_predict",seg.start,seg._end,st.predictions[i],"联想")
    cand.preedit = " "
    yield(cand)
  end
end

function M.filter.func(input, env)
  local st = state(env)
  local previous = st and preceding(st)
  if not st or not previous or st.predicting or not active(env) then
    for cand in input:iter() do yield(cand) end
    return
  end
  local scores = {}
  for rank,word in ipairs(ranked(st,previous,st.threshold)) do scores[word] = rank end
  if next(scores) == nil then for cand in input:iter() do yield(cand) end; return end
  local buffer, first, index = {}, nil, 0
  local function flush()
    table.sort(buffer,function(a,b)
      if a.rank == b.rank then return a.index < b.index end
      return a.rank < b.rank
    end)
    for _,item in ipairs(buffer) do yield(item.cand) end
  end
  -- Bounded lookahead, keeping the exact Candidate objects and coverage.
  for cand in input:iter() do
    index = index+1
    if index <= 32 then
      first = first or cand
      local rank = (cand.start == first.start and cand._end == first._end) and scores[cand.text]
      local genuine = cand:get_genuine()
      if genuine and genuine.type ~= 'phrase' and genuine.type ~= 'user_phrase'
          and genuine.type ~= 'sentence' then rank = nil end
      buffer[#buffer+1] = {cand=cand,index=index,rank=rank or 1000000}
    else
      if index == 33 then flush() end
      yield(cand)
    end
  end
  if index <= 32 then flush() end
end

return M
