
local currency = ARGV[1]
local user_id = ARGV[2]
local game_code = ARGV[3]

local pending_raw = redis.call('GETDEL', KEYS[3])
if not pending_raw or pending_raw == '' then
    redis.call('DEL', KEYS[2])
    return cjson.encode({error = 'nothing_to_collect'})
end

local pending = cjson.decode(pending_raw)
-- Prefer server-stored currency if present to prevent client manipulation
local stored_currency = pending.__currency or currency
local amount = tonumber(pending[stored_currency]) or 0
if amount <= 0 then
    redis.call('DEL', KEYS[2])
    return cjson.encode({error = 'nothing_to_collect2'})
end

local bal_raw = redis.call('GET', KEYS[1]) or '{}'
local bal = cjson.decode(bal_raw)
local current = tonumber(bal[stored_currency]['amount'] or '0') or 0
local new_balance = current + amount

bal[stored_currency]['amount'] = string.format("%.12f", new_balance)
redis.call('SET', KEYS[1], cjson.encode(bal))

redis.call('DEL', KEYS[2])
redis.call('DEL', KEYS[5])

local log_key = 'user:' .. user_id .. ':' .. game_code .. '_last_log'

local existing_raw = redis.call('GET', log_key)
local log_data = {}

if existing_raw and existing_raw ~= '' then
    log_data = cjson.decode(existing_raw)
end

log_data.game_status = 'win'

redis.call('SETEX', log_key, 60, cjson.encode(log_data))

return cjson.encode({
    action = 'collect',
    collected = string.format("%.12f", amount),
    balance = bal[stored_currency]['amount'],
    streak = 0
})
