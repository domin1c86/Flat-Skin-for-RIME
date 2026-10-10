-- 配套中英切换：最近使用的中文方案 <-> 独立英文 melt_eng。
-- 仅记录方案 ID 与英文候选开关，不保存输入文字。
local M = {}
local chinese = {double_pinyin_flypy=true, rime_mint=true, rime_mint_flypy=true}
local default_chinese = "double_pinyin_flypy"
local english = "melt_eng"
local cached = {}

local function read_memory(path)
  if cached[path] then return cached[path] end
  local config = Config()
  config:load_from_file(path)
  local id = config:get_string("last_chinese_schema")
  if not chinese[id] then id = default_chinese end
  local enabled = config:get_bool("english_candidates_enabled")
  if enabled == nil then enabled = true end
  cached[path] = {last_chinese_schema=id, english_candidates_enabled=enabled}
  return cached[path]
end

local function persist(path)
  local state = read_memory(path)
  local config = Config()
  config:load_from_file(path)
  if config:get_string("last_chinese_schema") ~= state.last_chinese_schema
      or config:get_bool("english_candidates_enabled") ~= state.english_candidates_enabled then
    config:set_string("last_chinese_schema", state.last_chinese_schema)
    config:set_bool("english_candidates_enabled", state.english_candidates_enabled)
    config:save_to_file(path)
  end
end

local function remember(path, id)
  if not chinese[id] then return end
  read_memory(path).last_chinese_schema = id
  persist(path)
end

function M.init(env)
  env.memory_path = rime_api.get_user_data_dir() .. "/skin_scheme_memory.yaml"
  read_memory(env.memory_path)
  local id = env.engine.schema.schema_id
  if chinese[id] then remember(env.memory_path, id)
  elseif id == english then
    env.engine.context:set_option("ascii_mode", not read_memory(env.memory_path).english_candidates_enabled)
  end
end

function M.func(key, env)
  -- 只响应专用组合键；松键不执行，其他字符不拦截。
  if key:release() or (key.keycode ~= 0xffc9 and key.keycode ~= 0xffc8) or not key:ctrl() or not key:shift()
      or key:alt() or key:super() then return 2 end
  local current = env.engine.schema.schema_id
  if key.keycode == 0xffc8 then
    if current ~= english then return 2 end
    local context = env.engine.context
    local enabled = context:get_option("ascii_mode")
    -- 不选补全候选：先清除预编辑，再将原始输入只提交一次。
    local raw = context.input or ""
    context:clear()
    if raw ~= "" then env.engine:commit_text(raw) end
    read_memory(env.memory_path).english_candidates_enabled = enabled
    persist(env.memory_path)
    context:set_option("ascii_mode", not enabled)
    return 1
  end
  local target
  if current == english then
    target = read_memory(env.memory_path).last_chinese_schema
  elseif chinese[current] then
    remember(env.memory_path, current)
    target = english
  else
    return 2
  end
  -- 先确认目标已部署，不能将空方案应用到引擎。
  local schema = Schema(target)
  if schema.config:get_string("schema/schema_id") ~= target then return 2 end
  -- 与切换方案一致：先确认当前预编辑，再切换，避免丢失已输入文字。
  local context = env.engine.context
  -- Direct hardware invocation also bypasses the skin's surrounding signals.
  -- A prediction is a menu suggestion, not text the user has chosen to commit.
  if context:get_option("skin_context_prediction") and context.input == "›" then
    context:clear()
    if context:get_option("skin_context_prediction") then
      context:set_option("skin_context_prediction", false)
    end
  end
  context:commit()
  env.engine:apply_schema(schema)
  env.engine.context:set_option("ascii_mode", target == english
      and not read_memory(env.memory_path).english_candidates_enabled or false)
  return 1
end

return M
