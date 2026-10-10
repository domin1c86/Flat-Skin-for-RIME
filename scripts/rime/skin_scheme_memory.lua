-- 配套中英切换：最近使用的中文方案 <-> 独立英文 melt_eng。
-- 仅记录方案 ID，不保存输入文字；不编辑 user.yaml 或词频数据库。
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
  cached[path] = id
  return id
end

local function remember(path, id)
  if not chinese[id] then return end
  local config = Config()
  config:load_from_file(path)
  cached[path] = id
  if config:get_string("last_chinese_schema") ~= id then
    config:set_string("last_chinese_schema", id)
    config:save_to_file(path)
  end
end

function M.init(env)
  env.memory_path = rime_api.get_user_data_dir() .. "/skin_scheme_memory.yaml"
  read_memory(env.memory_path)
  local id = env.engine.schema.schema_id
  if chinese[id] then remember(env.memory_path, id) end
end

function M.func(key, env)
  -- 只响应专用组合键；松键不执行，其他字符不拦截。
  if key:release() or key.keycode ~= 0xffc9 or not key:ctrl() or not key:shift()
      or key:alt() or key:super() then return 2 end
  local current = env.engine.schema.schema_id
  local target
  if current == english then
    target = read_memory(env.memory_path)
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
  env.engine.context:commit()
  env.engine:apply_schema(schema)
  env.engine.context:set_option("ascii_mode", false)
  return 1
end

return M
