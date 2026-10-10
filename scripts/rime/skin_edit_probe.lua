-- Isolated diagnostic only. Not installed by the normal companion bundle.
-- No dictionary updates, no text insertion, no consumed keys.
local P = {}
local function quote(text)
  local escapes = {['"']='\\"', ['\\']='\\\\', ['\n']='\\n', ['\r']='\\r', ['\t']='\\t'}
  return '"' .. tostring(text or ''):gsub('[%z\1-\31\\"]', function(c)
    return escapes[c] or string.format('\\u%04x',string.byte(c))
  end) .. '"'
end
local function record(env, event, text, code, key, input, script)
  if not env.path or env.count >= 256 then return end
  env.count = env.count+1
  local file = io.open(env.path,'a')
  if not file then return end
  file:write('{"event":',quote(event),',"text":',quote(text),',"code":',quote(code),
             ',"key":',quote(key),',"preedit_input":',quote(input),
             ',"script":',quote(script),',"time":',tostring(os.time()),'}\n')
  file:close()
end
function P.init(env)
  local config, ctx = env.engine.schema.config, env.engine.context
  env.count = 0
  if not config:get_bool('skin_edit_probe/enabled') then return end
  -- Fixed filename in the isolated user directory; never an arbitrary path.
  env.path = rime_api.get_user_data_dir() .. '/edit-probe.jsonl'
  record(env,'init')
  env.commit_connection = ctx.commit_notifier:connect(function(c)
    local ok, script = pcall(function() return c:get_script_text() end)
    record(env,'commit',c:get_commit_text(),c.input,nil,nil,ok and script or '')
  end)
end
function P.func(key,env)
  if env.path and not key:release() then
    record(env,'key',nil,nil,key:repr(),env.engine.context.input)
  end
  return 2
end
function P.fini(env)
  if env.commit_connection then env.commit_connection:disconnect() end
  if env.path then record(env,'engine_end') end
end
return P
