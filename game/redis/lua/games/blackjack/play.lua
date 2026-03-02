local balance_key = KEYS[1]
local log_key = KEYS[3]

local action = ARGV[1]
local user_id  = ARGV[2]
local currency = ARGV[3]

local GAME_TTL = 600
local LOG_TTL  = 600
local LOCK_TTL = 1
local RATE_TTL = 1

local rate_key = 'user:'..user_id..':bj_rate' -- Check fast requests
local game_lock_key = 'user:'..user_id..':bj_game_lock' -- Game already running
local bj_action_lock = 'user:'..user_id..':bj_action_lock' -- Hit stand lock
local deck_key = 'user:'..user_id..':blackjack_deck'
local game_key = 'user:'..user_id..':blackjack_game'


if not user_id or user_id == '' then
    return {error='invalid_user'}
end

if not redis.call('SET', rate_key, '1', 'NX', 'EX', RATE_TTL) then
    return {error='too_fast'}
end

local function seeded_random(h)
    local state = 0
    local pos = 1
    return function(max)
        if max <= 1 then return 1 end
        while true do
            if pos > #h then
                h = redis.sha1hex(tostring(state) .. h)
                pos = 1
            end
            local seg = h:sub(pos, pos + 7)
            pos = pos + 8
            if #seg == 8 then
                state = tonumber(seg, 16)
                return (state % max) + 1
            end
        end
    end
end

local function get_game_config()
    local config_game_json = redis.call('GET', 'game_config:blackjack')
    local multiplier, min_bet, max_bet = 2, 0.10, 1000
    if config_game_json then
        local cfg = cjson.decode(config_game_json)
        multiplier = tonumber(cfg.multiplier) or multiplier
        min_bet = tonumber(cfg.min_bet) or min_bet
        max_bet = tonumber(cfg.max_bet) or max_bet
    end

    return multiplier, min_bet, max_bet
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

local function create_deck(hash_hex, num_decks)
    num_decks = num_decks or 1

    local deck = {}

    for deck_idx = 1, num_decks do
        for suit = 1, 4 do
            for rank = 1, 13 do
                table.insert(deck, rank)
            end
        end
    end

    local rand = seeded_random(hash_hex)

    for i = #deck, 2, -1 do
        local j = rand(i)
        deck[i], deck[j] = deck[j], deck[i]
    end

    -- deck = {10, 10, 1, 5, 2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 10, 1}

    return deck
end

local function get_deck()
    local deck_str = redis.call('GET', deck_key)

    if deck_str then
        return cjson.decode(deck_str)
    else
        return false
    end
end

local function calc_score(hand)
    local total = 0
    local aces_count = 0

    for _, rank in ipairs(hand) do
        local val = rank
        if rank >= 10 then val = 10 end -- 10, 11(J), 12(Q), 13(K) -> 10
        if rank == 1 then val = 1 end   -- Ace -> 1 (adjusted later)

        if rank == 1 then
            aces_count = aces_count + 1
        end
        total = total + val
    end

    if aces_count > 0 and total + 10 <= 21 then
        total = total + 10
    end

    return total
end

local function draw_card(deck, hand)
    local card = table.remove(deck, 1)
    table.insert(hand, card)
end

local function update_status(game, action)
    local dealer_score = calc_score(game.dealer.hand)
    if game.player.hands[2] then
        redis.log(redis.LOG_NOTICE, 'player_score_hand_first ' .. tostring(game.player.hands[2].status_game))
    end

    if game.player.hands[2] then
        local hand1 = game.player.hands[1]
        local hand2 = game.player.hands[2]
        local dealer_score = calc_score(game.dealer.hand)
        local score1 = calc_score(hand1.hand)
        local score2 = calc_score(hand2.hand)

        if score1 > 21 then
            hand1.status_game = 'lose'
            score1 = 0
        end

        if score2 > 21 then
            hand2.status_game = 'lose'
            score2 = 0
        end

        if score1 == 21 then hand1.status_game = 'win' end
        if score2 == 21 then hand2.status_game = 'win' end

        if hand1.status_game == 'ongoing' or hand2.status_game == 'ongoing' then
            return game
        end

        -- Перебор дилера
        if dealer_score > 21 then
            game.dealer.status_game = 'lose'
            if hand1.status_game ~= 'lose' then hand1.status_game = 'win' end
            if hand2.status_game ~= 'lose' then hand2.status_game = 'win' end
        else
            -- Победа дилера
            if dealer_score > score1 and score1 <= 21 then hand1.status_game = 'lose' end
            if dealer_score > score2 and score2 <= 21 then hand2.status_game = 'lose' end

            if dealer_score > score1 and dealer_score > score2 then
                game.dealer.status_game = 'win'
            elseif dealer_score == score1 or dealer_score == score2 then
                game.dealer.status_game = 'draw'
            elseif dealer_score < score1 or dealer_score < score2 then
                game.dealer.status_game = 'lose'
            else
                game.dealer.status_game = 'ongoing'  -- если нет выигрыша и ничьи
            end
        end

        if score1 > dealer_score and score1 <= 21 then hand1.status_game = 'win' end
        if score2 > dealer_score and score2 <= 21 then hand2.status_game = 'win' end

        if score1 == dealer_score and score1 <= 21 then hand1.status_game = 'draw' end
        if score2 == dealer_score and score2 <= 21 then hand2.status_game = 'draw' end

        redis.log(redis.LOG_NOTICE, 'score1 ' .. tostring(score1))
        redis.log(redis.LOG_NOTICE, 'score2 ' .. tostring(score2))
        redis.log(redis.LOG_NOTICE, 'dealer_score ' .. tostring(dealer_score))

        return game
    elseif not game.player.hands[2] then -- Если игра с одной рукой
        local player_score = calc_score(game.player.hands[1].hand)
        if action == 'create' then
            if player_score == 21 then
                if dealer_score == 21 then
                    game.player.hands[1].status_game = 'draw'
                    game.dealer.status_game = 'draw'
                else
                    game.player.hands[1].status_game = 'win'
                    game.dealer.status_game = 'lose'
                end
            end
        elseif action == 'hit' then
            if player_score == 21 then
                game.player.hands[1].status_game = 'win'
                game.dealer.status_game = 'ongoing'
            elseif player_score > 21 then
                game.player.hands[1].status_game = 'lose'
                game.dealer.status_game = 'ongoing'
            end
        elseif action == 'stand' then
            if player_score == 21 then
                game.player.hands[1].status_game = 'win'
                game.dealer.status_game = 'ongoing'
            elseif player_score > 21 then
                game.player.hands[1].status_game = 'lose'
                game.dealer.status_game = 'ongoing'
            elseif dealer_score > 21 then
                game.dealer.status_game = 'lose'
                game.player.hands[1].status_game = 'win'
            elseif dealer_score > player_score then
                game.dealer.status_game = 'win'
                game.player.hands[1].status_game = 'lose'
            elseif dealer_score < player_score then
                game.dealer.status_game = 'lose'
                game.player.hands[1].status_game = 'win'
            elseif dealer_score == player_score then
                game.dealer.status_game = 'draw'
                game.player.hands[1].status_game = 'draw'
            end
        end
    end

    return game
end

local function get_game()
    local game_json = redis.call('GET', game_key)
    if game_json then
        return cjson.decode(game_json)
    end

    return false
end

local function stop_game()
    redis.call('DEL', deck_key)
    redis.call('DEL', game_key)
    redis.call('DEL', rate_key)
    redis.call('DEL', game_lock_key)
end

local function calculate_win_result(game, multiplier)
    local won = 0
    for _, hand in ipairs(game.player.hands or {}) do
        if hand and hand.bet then
            local bet = tonumber(hand.bet)
            if hand.status_game == 'win' then
                won = won + bet * multiplier
            elseif hand.status_game == 'draw' then
                won = won + bet
            end
        end
    end

    return won
end

local function calculate_total_bet(game)
    local total = 0
    for _, hand in ipairs(game.player.hands or {}) do
        if hand and hand.bet then
            total = total + tonumber(hand.bet)
        end
    end
    return total
end

local function set_log(game_arg)
    if type(game_arg) ~= 'table' or game_arg.error then
        return
    end

    local multiplier, min_bet, max_bet = get_game_config()

    local function update_log_status(log_data, game)
        local all_hands_finished = true
        for _, h in ipairs(game.player.hands) do
            if h.status_game == 'ongoing' then
                all_hands_finished = false
                break
            end
        end

        if game.dealer.status_game == 'ongoing' and not all_hands_finished then
            log_data.game_status = 'ongoing'
        else
            local payout = calculate_win_result(game, multiplier)
            local total_bet = calculate_total_bet(game)

            log_data.payout = string.format('%.12f', payout)
            log_data.bet_amount = string.format('%.12f', total_bet)

            if payout > total_bet then
                log_data.game_status = 'win'
            elseif payout == total_bet then
                log_data.game_status = 'draw'
            else
                log_data.game_status = 'lose'
            end
        end
        return log_data
    end

    if action == 'create' then
        local pf_data = redis.call('HMGET', KEYS[2], 'server_seed', 'client_seed', 'nonce')
        local current_nonce = tonumber(pf_data[3] or '0')

        local log_data = {
            user_fk_id = ARGV[2],
            pf_chain_fk_id = ARGV[7],
            bet_amount = ARGV[4],
            payout = string.format('%.12f', 0),
            game_status = 'ongoing',
            multiplier = string.format('%.2f', multiplier),
            nonce = current_nonce,
        }

        local game = game_arg
        if game then
            log_data = update_log_status(log_data, game)
        end

        redis.call('SETEX', log_key, LOG_TTL, cjson.encode(log_data))
    else
        local game = game_arg
        local all_hands_finished = true
        if game and game.player and game.player.hands then
            for _, h in ipairs(game.player.hands) do
                if h.status_game == 'ongoing' then
                    all_hands_finished = false
                    break
                end
            end
        end

        if game and (game.dealer.status_game ~= 'ongoing' or all_hands_finished) then
            local log_json = redis.call('GET', log_key)
            if log_json then
                local log_current = cjson.decode(log_json)
                log_current = update_log_status(log_current, game)
                redis.call('SETEX', log_key, 60, cjson.encode(log_current))
            end
        end
    end
end

local ok, result = pcall(function()
    if action == 'create' then
        local lock = redis.call('SET', game_lock_key, '1', 'NX', 'EX', GAME_TTL)
        if not lock then
            local game = get_game()
            return game
        end

        local pf_data = redis.call('HMGET', KEYS[2], 'server_seed', 'client_seed', 'nonce')
        local bet = tonumber(ARGV[4])
        local hash_hex = ARGV[5]

        local server_seed, client_seed, current_nonce = pf_data[1], pf_data[2], tonumber(pf_data[3] or '0')
        local multiplier, min_bet, max_bet = get_game_config()
        local balance = get_balance()

        if not bet or bet <= 0 or bet < min_bet or bet > max_bet or balance < bet then
            error({error='invalid_bet'})
        end

        if not hash_hex or #hash_hex ~= 64 then
            error({error='invalid_hash'})
        end

        if not server_seed or not client_seed then
            error({error='pf_missing_seeds'})
        end

        -- Currency for this game is stored in game object; no global lock here

        local deck = get_deck()

        if not deck then
            deck = create_deck(hash_hex)
            redis.call('HSET', KEYS[2], 'nonce', current_nonce + 1)
            balance = adjust_balance(-bet)
        end

        local game = get_game()

        if not game then
            game = {
                balance=string.format('%.12f', balance),
                bet = string.format('%.12f', bet),
                currency = currency,
                player = {
                    hands = {{
                        hand = {},
                        status_game = 'ongoing',
                        bet = string.format('%.12f', bet),
                        double_used = false,
                    }},
                    split_used = false,
                },
                dealer = {hand = {}, status_game = 'ongoing'},
            }

            for i = 1, 2 do
                draw_card(deck, game.player.hands[1].hand)
                draw_card(deck, game.dealer.hand)
            end

            update_status(game, 'create')

            local won = calculate_win_result(game, multiplier)

            if won == 0 then
                redis.call('SETEX', deck_key, GAME_TTL, cjson.encode(deck))
                redis.call('SETEX', game_key, GAME_TTL, cjson.encode(game))
            else
                local new_balance = adjust_balance(won)
                game.balance = string.format('%.12f', new_balance)
                stop_game()
                redis.call('DEL', game_lock_key)
            end
        end

        return game

    elseif action == 'hit' or action == 'stand' then
        local lock = redis.call('SET', bj_action_lock, '1', 'NX', 'EX', LOCK_TTL)
        if not lock then
            return {error='action_locked'}
        end

        local multiplier, min_bet, max_bet = get_game_config()
        local game = get_game()
        local deck = get_deck()

        if not game then
            error({error='game_not_found'})
        end

        if not deck then
            error({error='deck_not_found'})
        end

        -- Use currency stored in game to process this blackjack session
        currency = game.currency
        local balance = get_balance()

        local player_index = 1

        if game.player.split_used and game.player.hands[1].status_game ~= 'ongoing' then
            player_index = 2
        end

        if action == 'hit' then
            draw_card(deck, game.player.hands[player_index].hand)
            update_status(game, action)
        elseif action == 'stand' then
            game.player.hands[player_index].status_game = 'stand'
        end

        local function finish_hand(hand)
            while calc_score(game.dealer.hand) < 17 do
                draw_card(deck, game.dealer.hand)
            end

            update_status(game, action)
            local won = calculate_win_result(game, multiplier)
            local new_balance = adjust_balance(won)
            game.balance = string.format('%.12f', new_balance)

            stop_game()
            redis.call('DEL', game_lock_key)
            return game
        end

        local hand_to_process
        if game.player.split_used then
            hand_to_process = game.player.hands[2]
        else
            hand_to_process = game.player.hands[player_index]
        end

        if hand_to_process.status_game ~= 'ongoing' then
            return finish_hand(hand_to_process)
        end

        redis.call('SETEX', deck_key, GAME_TTL, cjson.encode(deck))
        redis.call('SETEX', game_key, GAME_TTL, cjson.encode(game))

        return game
    elseif action == 'double' then
        local lock = redis.call('SET', bj_action_lock, '1', 'NX', 'EX', LOCK_TTL)
        if not lock then
            return {error='action_locked'}
        end

        local multiplier, min_bet, max_bet = get_game_config()
        local game = get_game()
        local deck = get_deck()

        if not game then
            error({error='game_not_found'})
        end

        if not deck then
            error({error='deck_not_found'})
        end

        -- Use currency stored in game to process this blackjack session
        currency = game.currency
        local balance = get_balance()

        -- if game.player.hands[1].status_game ~= 'ongoing' then
        --     error({error='game_already_ended'})
        -- end

        local current_bet = tonumber(game.bet)

        if balance < current_bet then
            error({error='insufficient_balance'})
        end

        local player_index = 1

        if game.player.split_used and game.player.hands[1].status_game ~= 'ongoing' then
            player_index = 2
        end

        if #game.player.hands[player_index].hand ~= 2 then
            error({error='double_not_allowed'})
        end

        if game.player.hands[player_index].double_used then
            error({error='double_already_used', tt=game.player.hands})
        end

        game.player.hands[player_index].double_used = true
        redis.call('SETEX', game_key, GAME_TTL, cjson.encode(game))

        balance = adjust_balance(-current_bet)
        game.player.hands[player_index].bet = string.format('%.12f', current_bet * 2)
        game.balance = string.format('%.12f', balance)
        game.player.hands[player_index].status_game = 'stand'
        draw_card(deck, game.player.hands[player_index].hand)
        update_status(game, 'stand')

        local function finish_hand(hand)
            while calc_score(game.dealer.hand) < 17 do
                draw_card(deck, game.dealer.hand)
            end

            update_status(game, 'stand')
            local won = calculate_win_result(game, multiplier)
            local new_balance = adjust_balance(won)
            game.balance = string.format('%.12f', new_balance)
            stop_game()
            redis.call('DEL', game_lock_key)
            return game
        end

        local hand_to_process
        if game.player.split_used then
            hand_to_process = game.player.hands[2]
        else
            hand_to_process = game.player.hands[player_index]
        end

        if hand_to_process.status_game ~= 'ongoing' then
            return finish_hand(hand_to_process)
        end

        redis.call('SETEX', deck_key, GAME_TTL, cjson.encode(deck))
        redis.call('SETEX', game_key, GAME_TTL, cjson.encode(game))

        return game

    elseif action == 'split' then
        local lock = redis.call('SET', bj_action_lock, '1', 'NX', 'EX', LOCK_TTL)
        if not lock then
            return {error='action_locked'}
        end

        -- Prevent actions if currency was changed for this user's game
        -- Use game's stored currency and compute balance after fixing currency
        local game = get_game()
        local deck = get_deck()

        if not game then error({error='game_not_found'}) end
        if not deck then error({error='deck_not_found'}) end

        currency = game.currency
        local balance = get_balance()

        if #game.player.hands[1].hand ~= 2 then
            error({error='invalid_hand_size_for_split'})
        end

        local card1 = game.player.hands[1].hand[1]
        local card2 = game.player.hands[1].hand[2]
        if card1 ~= card2 then
            error({error='split_card_mismatch'})
        end

        if game.player.split_used then
            error({error='split_already_used'})
        end

        local split_bet = tonumber(game.bet)

        if balance < split_bet then
            error({error='insufficient_balance'})
        end

        adjust_balance(-split_bet)

        game.player.split_used = true
        local first_hand_cards = game.player.hands[1].hand

        game.player.hands[2] = {
            hand = { first_hand_cards[2] },
            status_game = 'ongoing',
            bet = game.player.hands[1].bet,
            double_used = false
        }
        game.player.hands[1].hand = { first_hand_cards[1] }

        draw_card(deck, game.player.hands[1].hand)
        draw_card(deck, game.player.hands[2].hand)

        update_status(game, 'split')

        redis.call('SETEX', game_key, GAME_TTL, cjson.encode(game))
        redis.call('SETEX', deck_key, GAME_TTL, cjson.encode(deck))

        return game
    end
end)

if not ok then
    redis.call('DEL', game_lock_key)
end

if ok and type(result) == 'table' and result.dealer then
    if result.dealer.status_game == 'ongoing' then
        local upcard = { result.dealer.hand[1] }
        result.dealer.total = calc_score(upcard)
    else
        result.dealer.total = calc_score(result.dealer.hand)
    end

    if result.player and result.player.hands then
        for _, hand in ipairs(result.player.hands) do
            hand.total = calc_score(hand.hand)
        end
    end
end

if ok then
    set_log(result)
end

return cjson.encode(result)
