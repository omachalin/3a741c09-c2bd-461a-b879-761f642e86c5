
local currency = ARGV[1]
local bet = tonumber(ARGV[2])
local choice = tonumber(ARGV[3])
local hash = ARGV[4]
local next_nonce = ARGV[5]
local user_id = ARGV[6]
local chain_drf_id = ARGV[7]
local game_code = ARGV[8]

if choice ~= 0 and choice ~= 1 then
    return cjson.encode({error='invalid_choice'})
end
if not bet or bet <= 0 then
    return cjson.encode({error='invalid_bet'})
end
if not hash or #hash ~= 64 then
    return cjson.encode({error='invalid_hash'})
end
if not next_nonce or not tonumber(next_nonce) then
    return cjson.encode({error='invalid_nonce'})
end

-- Проверка start_bet
local start_bet = tonumber(redis.call('GET', KEYS[5]) or 0)
if start_bet > 0 and start_bet ~= bet then
    bet = start_bet
end

-- Сохраняем первоначальную ставку, если ещё не установлена
if start_bet == 0 then
    redis.call('SET', KEYS[5], bet)
end

local config_json = redis.call('GET', 'game_config:coin_flip')

local multiplier = 1.95
local min_bet = 0.10
local max_bet = 5000

if config_json then
    local config = cjson.decode(config_json)

    if config.multiplier then
        multiplier = tonumber(config.multiplier) or multiplier
    end
    if config.min_bet then
        min_bet = tonumber(config.min_bet) or min_bet
    end
    if config.max_bet then
        max_bet = tonumber(config.max_bet) or max_bet
    end
end

if bet < min_bet or bet > max_bet then
    return cjson.encode({error='invalid_bet_amount', bet=bet, min_bet=min_bet, max_bet=max_bet})
end

local balances_json = redis.call('GET', KEYS[1]) or '{}'
local balances = cjson.decode(balances_json)
local balance = tonumber(balances[currency]['amount'] or 0) or 0

if balance < bet then
    return cjson.encode({
        error = 'insufficient_balance',
        balance = balance,
        bet = bet
    })
end

balance = balance - bet
balances[currency]['amount'] = string.format("%.12f", balance)
redis.call('SET', KEYS[1], cjson.encode(balances))

local pf_data = redis.call('HMGET', KEYS[4], 'server_seed', 'client_seed', 'nonce')
local server_seed = pf_data[1]
local client_seed = pf_data[2]
local current_nonce = pf_data[3] or '0'

if not server_seed or not client_seed then
    return cjson.encode({error='pf_missing_seeds'})
end

if tostring(tonumber(current_nonce) + 1) ~= next_nonce then
    return cjson.encode({error='nonce_mismatch'})
end

redis.call('HSET', KEYS[4], 'nonce', next_nonce)

local hex_prefix = hash:sub(1, 8)
local num = tonumber(hex_prefix, 16)
local result = num % 2

local streak = tonumber(redis.call('GET', KEYS[2]) or '0') or 0
local win = (result == choice)
local payout = 0
local final_multiplier = 0

if win then
    streak = streak + 1
    redis.call('SET', KEYS[2], tostring(streak), 'EX', 900)

    final_multiplier = multiplier ^ streak
    if final_multiplier > 20 then
        final_multiplier = 20
    end

    payout = bet * final_multiplier

    local pending = {__currency = currency}
    pending[currency] = payout
    redis.call('SET', KEYS[3], cjson.encode(pending), 'EX', 600)

else
    redis.call('DEL', KEYS[2])
    redis.call('DEL', KEYS[3])
    redis.call('DEL', KEYS[5])
    streak = 0
    payout = 0
    final_multiplier = 0
end

local log_key = "user:" .. user_id .. ":" .. game_code .. "_last_log"

local log_data = {
    user_fk_id = user_id,
    pf_chain_fk_id = chain_drf_id,
    bet_amount = bet,
    payout = string.format('%.12f', payout),
    multiplier = string.format('%.2f', final_multiplier),
    nonce = next_nonce,
    game_status = win and 'ongoing' or 'lose'
}

redis.call("SETEX", log_key, 60, cjson.encode(log_data))

return cjson.encode({
    win = win,
    bet = bet,
    result = result,
    streak = streak,
    multiplier = string.format('%.2f', final_multiplier),
    potential_payout = string.format("%.12f", payout),
    balance = balances[currency]['amount'],
    pending_available = win and payout > 0,
    provably_fair = {
        client_seed = client_seed,
        -- nonce = current_nonce,
        hash = hash
    }
})

