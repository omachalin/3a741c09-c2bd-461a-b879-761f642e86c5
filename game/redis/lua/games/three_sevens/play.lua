
local balance_key = KEYS[1]
local log_key = KEYS[3]

local action = ARGV[1]
local user_id  = ARGV[2]
local currency = ARGV[3]

local game_config_key = 'game_config:777'

local config_game_str = redis.call('GET', game_config_key)
local rate_key = 'user:'..user_id..':three_sevens_rate' -- Check fast requests
local RATE_TTL = 1
local LOG_TTL  = 600

if not redis.call('SET', rate_key, '1', 'NX', 'EX', RATE_TTL) then
    return cjson.encode({error='too_fast'})
end

local function get_game_config()
    local config_game_json = redis.call('GET', game_config_key)
    local min_bet, max_bet = 10, 2000
    if config_game_json then
        local cfg = cjson.decode(config_game_json)
        min_bet = tonumber(cfg.min_bet) or min_bet
        max_bet = tonumber(cfg.max_bet) or max_bet
    end

    return min_bet, max_bet
end

local function get_balance_table()
    local balances_json = redis.call('GET', balance_key) or '{}'
    local balances = cjson.decode(balances_json)

    local current_balance = tonumber(balances[currency].amount) or 0
    return balances, current_balance
end

local function get_balance()
    local _, current_balance = get_balance_table()
    return current_balance
end

local function adjust_balance(amount)
    local balances, current_balance = get_balance_table()

    current_balance = current_balance + amount
    balances[currency].amount = string.format("%.12f", current_balance)

    redis.call('SET', balance_key, cjson.encode(balances))
    return current_balance
end

local function pf_roll(server_seed, client_seed, nonce)
    local hash = redis.sha1hex(server_seed .. ':' .. client_seed .. ':' .. nonce)
    local roll = tonumber(hash:sub(1, 13), 16) % 999 + 1
    return roll
end

local function get_multiplier(user_number, multipliers)
    for pattern, multiplier in pairs(multipliers) do
        local match = true
        for i = 1, #pattern do
            local p = pattern:sub(i,i)
            local u = user_number:sub(i,i)
            if p ~= "*" and p ~= u then
                match = false
                break
            end
        end
        if match then
            return multiplier, pattern
        end
    end
    return 0, false
end

local ok, result = pcall(function()
    if not config_game_str then
        error({error='NO SUCH KEY: game_config:777'})
    end

    local config_game_json = cjson.decode(config_game_str)
    if not config_game_json then
        error({error='INVALID JSON: game_config:777'})
    end

    if config_game_json['multipliers'] == nil then
        error({error='INVALID MULTIPLIERS CONFIGURATION'})
    end

    local bet = tonumber(ARGV[4])

    local min_bet, max_bet = get_game_config()
    local balance = get_balance()

    if not bet or bet <= 0 or bet < min_bet or bet > max_bet then
        error({error='invalid_bet'})
    end

    if balance < bet then
        error({error='insufficient_balance'})
    end

    local multipliers = cjson.decode(config_game_json['multipliers'])

    local pf_data = redis.call('HMGET', KEYS[2], 'server_seed', 'client_seed', 'nonce')
    local server_seed, client_seed, current_nonce = pf_data[1], pf_data[2], tonumber(pf_data[3] or '0')

    if not server_seed or not client_seed then
        error({error='pf_missing_seeds'})
    end

    local next_nonce = tonumber(current_nonce) + 1
    local roll_number = pf_roll(server_seed, client_seed, next_nonce)
    local roll_str = string.format("%03d", roll_number)
    redis.call('HINCRBY', KEYS[2], 'nonce', 1)

    local log_data = {
        user_fk_id = user_id,
        pf_chain_fk_id = ARGV[7],
        bet_amount = ARGV[4],
        payout = 0,
        game_status = 'lose',
        multiplier = 0,
        nonce = next_nonce,
        game_data = {
            roll_number = roll_str
        }
    }

    local multiplier, win_mask = get_multiplier(string.format("%03d", roll_number), multipliers)
    log_data.win_mask = win_mask
    log_data.game_data['win_mask'] = win_mask

    if multiplier > 0 then
        local payout = tonumber(ARGV[4]) * multiplier

        log_data.payout = string.format('%.12f', payout)
        log_data.multiplier = string.format('%.2f', multiplier)
        log_data.game_status = 'win'
    end

    balance = adjust_balance(tonumber(log_data.payout) - bet)
    redis.call('SETEX', log_key, LOG_TTL, cjson.encode(log_data))

    return {
        game_status = log_data.game_status,
        bet = log_data.bet_amount,
        currency = currency,
        balance = balance,
        roll_number = roll_str,
        multiplier = multiplier,
        payout = log_data.payout,
        win_mask = log_data.win_mask,
    }

end)

if not ok then
    return cjson.encode({error = result.error or "execution_error"})
end

return cjson.encode(result)
