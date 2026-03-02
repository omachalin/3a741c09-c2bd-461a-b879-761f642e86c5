local balance_key = KEYS[1]
local pf_key = KEYS[2]
local log_key = KEYS[3]

local user_id  = ARGV[1]
local currency = ARGV[2]
local bet = tonumber(ARGV[3])
local hash_hex = ARGV[4]
local current_nonce = tonumber(ARGV[5]) or 0

local fruits_count = 13
local scatter_index = 10
local wild_index = 11

local function get_game_config()
    local config_game_str = redis.call('GET', 'game_config:slots_fruit')
    local min_bet, max_bet, cols, rows, paytable, paylines = 10, 2000, 5, 3, {}, {}

    if config_game_str then
        local cfg = cjson.decode(config_game_str)
        min_bet = tonumber(cfg.min_bet) or min_bet
        max_bet = tonumber(cfg.max_bet) or max_bet
        cols = tonumber(cfg.reels.cols) or cols
        rows = tonumber(cfg.reels.rows) or rows
        paytable = cfg.paytable or paytable
        paylines = cfg.paylines or paylines
    end

    return min_bet, max_bet, cols, rows, paytable, paylines
end

local function get_balance()
    local balances_json = redis.call('GET', balance_key) or '{}'
    local balances = cjson.decode(balances_json)
    return tonumber(balances[currency].amount) or 0, balances
end

local function adjust_balance(amount)
    local current_balance, balances = get_balance()
    current_balance = current_balance + amount
    balances[currency].amount = string.format("%.12f", current_balance)
    redis.call('SET', balance_key, cjson.encode(balances))
    return current_balance
end

local function generate_pf_matrix(rows, cols, hash_hex, nonce)
    if not hash_hex or #hash_hex < 40 then
        return redis.error_reply("Invalid or too short hash_hex")
    end

    local matrix = {}
    local pos = 1

    for r = 1, rows do
        matrix[r] = {}
        for c = 1, cols do
            local chunk = string.sub(hash_hex, pos, pos + 7)
            if #chunk < 4 then
                chunk = string.sub(hash_hex, 1, 8)
            end

            local value = tonumber("0x"..chunk)
            local num = value % (fruits_count-2)

            if num == wild_index then
                matrix[r][c] = wild_index
            elseif num == scatter_index then
                matrix[r][c] = scatter_index
            else
                matrix[r][c] = num
            end

            pos = pos + 8
            if pos > #hash_hex then pos = 1 end
        end
    end

    redis.call('HSET', pf_key, 'nonce', nonce + 1)

    return matrix, nonce + 1
end

local function calculate_wins(matrix, paylines, paytable, bet)
    local total_win = 0
    local scatter_count = 0

    for r=1,#matrix do
        for c=1,#matrix[r] do
            if matrix[r][c] == scatter_index then
                scatter_count = scatter_count + 1
            end
        end
    end

    local scatter_win = 0
    if paytable[tostring(scatter_index)] then
        local scatter_pt = paytable[tostring(scatter_index)].paytable
        if scatter_pt[tostring(scatter_count)] then
            scatter_win = scatter_pt[tostring(scatter_count)] * bet
        end
    end
    total_win = total_win + scatter_win

    for li=1,#paylines do
        local line = paylines[li].path
        local first_row, first_col = line[1][1]+1, line[1][2]+1
        local first_symbol = matrix[first_row][first_col]
        local count = 1

        for p=2,#line do
            local r, c = line[p][1]+1, line[p][2]+1
            local s = matrix[r][c]
            if s == first_symbol or s == wild_index then
                count = count + 1
            else
                break
            end
        end

        local sym_pt = paytable[tostring(first_symbol)]
        if sym_pt and sym_pt.paytable then
            local win_for_line = sym_pt.paytable[tostring(count)]
            if win_for_line then
                total_win = total_win + win_for_line * bet
            end
        end
    end

    return total_win, scatter_count
end

local ok, result = pcall(function()
    local min_bet, max_bet, cols, rows, paytable, paylines = get_game_config()
    local balance = get_balance()

    if not bet or bet <= 0 or bet < min_bet or bet > max_bet then
        error('invalid_bet')
    end

    if balance < bet then
        error('insufficient_balance')
    end

    local new_balance = adjust_balance(-bet)

    local matrix, new_nonce = generate_pf_matrix(rows, cols, hash_hex, current_nonce)

    local total_win, scatter_count = calculate_wins(matrix, paylines, paytable, bet)

    return {
        matrix = matrix,
        total_win = total_win,
        scatter_count = scatter_count,
        balance = new_balance,
    }
end)

if not ok then
    return cjson.encode({error = tostring(result)})
end

return cjson.encode(result)
