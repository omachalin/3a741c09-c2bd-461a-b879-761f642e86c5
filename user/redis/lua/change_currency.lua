-- KEYS[1] = user:{id}:current_currency
-- ARGV[1] = new_currency (string)
-- ARGV[2] = user_id (string)

local currency_key = KEYS[1]
local new_currency = ARGV[1]
local user_id = ARGV[2]

if not user_id or user_id == '' then
    return cjson.encode({error='invalid_user'})
end

if not new_currency or new_currency == '' then
    return cjson.encode({error='invalid_currency'})
end

-- local currency_lock_key = 'user:'..user_id..':bj_currency_lock'

-- local cur_lock = redis.call('GET', currency_lock_key)
-- if cur_lock and cur_lock ~= new_currency then
--     return cjson.encode({error='currency_locked'})
-- end

local prev = redis.call('GET', currency_key)
redis.call('SET', currency_key, new_currency)

return cjson.encode({ok='ok', previous = prev, current = new_currency})
