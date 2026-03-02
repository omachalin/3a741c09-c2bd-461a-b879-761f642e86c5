local balance = redis.call('GET', KEYS[1])
local current_currency = redis.call('GET', KEYS[2])

if not balance then
    return '{}'
end

if not current_currency then
    current_currency = nil
end

local balances_json = cjson.decode(balance)

return cjson.encode({
    balances = balances_json,
    current_currency = current_currency
})
