"""
Executive Summary
=================
This is a readable, Python-inspired reconstruction of tuttifrutti.prg.
The game logic runs in a raster interrupt. There are six maps, three recurring
rule variants, at most five simultaneously active enemies, a bouncing shot,
and two kinds of moving blocks.

READING ORDER
1. Data model and terminology
2. start() -> frame_tick() -> play_one_tick()
3. Movement, map, shot, enemies and blocks
4. Level goals, score, death, rendering and music
5. Limits of the reconstruction

This is NOT an executable Python game. Objects such as `game`, `player`,
`map`, `screen` and `audio` group related memory locations. Assignments to these
objects represent changes to the original state. Named character, graphics and
sound operations are explanatory abstractions. The function names were assigned
during analysis; the original names have not survived.

Source: exclusively the specific PRG file in this repository.
SHA-256: 63ba58701faf770d0305214e5a0aed384e9c92b6fd8afa70377e7ed2645955e7
$1234 denotes an ORIGINAL MEMORY ADDRESS in hexadecimal, not a line number.
The more directly traceable instruction sequence is in analysis/disassembly.txt.

Confidence labels:
  VERIFIED   = directly derived from instructions, memory accesses and data.
  SIMPLIFIED = the same idea expressed with a clearer data structure;
               8-bit arithmetic edge cases need not be identical.
  INFERRED   = meaning/name inferred from usage or graphics.
  OPEN       = unusual behavior whose actual effect remains unresolved.

Important simplification: the original also uses screen characters as numeric
storage! `game.score`, `game.lives`, `game.bonus` and the clock below are readable
stand-ins for those characters.
"""


# ---------------------------------------------------------------------------
# 1. DATA MODEL AND TERMINOLOGY
# ---------------------------------------------------------------------------

WIDTH = 16                         # Map: 16 × 12 logical tiles.
HEIGHT = 12
UNITS_PER_TILE = 8              # Internal movement units, NOT pixels.
# One map tile uses 2 × 2 screen characters, or 16 × 16 pixels.
# One internal movement unit therefore equals 2 screen pixels.

EMPTY = 0
EARTH = 1
CHERRY = 2
APPLE = 3                          # Stationary/falling apple; blocks walking.
CHERRY_BLOCK = 4                     # Pushable; breaks when obstructed.
APPLE_BLOCK = 5                      # Pushable; does not break when pushed.
WALL_6 = 6                         # Fixed barrier with its own color.
WALL_7 = 7                         # Another fixed barrier; see goal checks.
OUTSIDE = 15                    # Returned by the map reader outside the map.
# Names for types 1, 3, 4 and 5 are inferred from behavior and graphics.
# In particular, do not assume WALL_7 is an "invisible wall" without evidence.

LEFT, RIGHT, UP, DOWN = 0, 1, 2, 3
STEP = {LEFT: (-1, 0), RIGHT: (1, 0), UP: (0, -1), DOWN: (0, 1)}
OPPOSITE = {LEFT: RIGHT, RIGHT: LEFT, UP: DOWN, DOWN: UP}
DIRECTION_BIT = {LEFT: 4, RIGHT: 8, UP: 1, DOWN: 2}  # $3EF4, $3EF8, $3EFC

# The original combines a direction number with a stop bit:
#   $00..$03: move actively in this direction
#   $80..$83: stop while retaining the facing direction
#   $FF:      inactive figure
# The pseudocode separates these into direction, stopped and active.

# `game` groups the following state:
#   mode              $E2: 0=title; 1,3,5=transition; 2,4,6=playing; 7=game over
#                     Bit 7 ($80) additionally marks the death sequence.
#   tick              $E7: running 8-bit frame counter, wraps from 255 to 0
#   transition        $E6: wait/music counter at startup and round transitions
#   map_index         $E5: 0..5, selects one of the six playable maps
#   difficulty_level  $B6: keeps increasing when the maps repeat
#   death_pause       $90: countdown for death or game over
#   score             five digits at $0C4A..$0C4E
#   lives             one digit at $0DB6
#   bonus             three digits at $0D3A..$0D3C
#   round_number      two digits at $0E2A..$0E2B
#   clock             characters at $0CC2..$0CC7, subtick at $B5
#   reserves          $8C: additional enemies not yet scheduled to appear
#   enemy_speed       $88: increment for an 8-bit timing accumulator
#   enemy_clock       $87: current value of that accumulator
#   bonus_half_tick   $B4: bonus decreases every second enemy movement tick
#   random_state      $89..$8B: three bytes
#   highscore_rank    $B7: 0..7, or 8=no rank yet

# `player` is figure 0; figures 1..5 are enemies.
# `figures` and `enemies` below refer to the same table, ordered by original
# index: enemies[1:6] are the five enemies; index 0 is the player.
# Memory is reserved for eight entries; rendering and AI use six.
# Fields in a figure entry:
#   x                 $0360 + figure_index
#   y                 $0368 + figure_index
#   direction/stopped $0370 + figure_index
#   spawn_countdown   $04F0 + figure_index; $FF=no appearance scheduled

# `objects[0..7]` are other moving items, separate from the figures:
#   x                 $0340 + index
#   y                 $0348 + index
#   dx                $0350 + index
#   dy                $0358 + index
#   fall_delay        $0338 + index
#   direction/active  $0378 + index; $FF=inactive
# Slots 0..5: six apples placed in the level that can fall.
# Slot 7: the single block currently being pushed. Slot 6 has no clear main role.

# `shot` groups $6A..$71:
#   dx, dy            $6A, $6B
#   status            $6C: 0=ready, $C0=flying, otherwise recharge countdown
#   x, y              $6D, $6E
#   has_left_player_tile $71: has the shot already left the player's tile?

# `breaking` groups $65..$69: time left, screen address and tile coordinates.
# `game.sliding_type` ($64) is 0 for apple blocks, $28 for cherry block graphics.
# `controls`: direction bits 0..3 plus fire; fire is active-low in the original.
# `sfx`: frequency ($83), change ($84), duration ($85), short tone pause ($86).


# ---------------------------------------------------------------------------
# 2. STARTUP AND MAIN FLOW
# ---------------------------------------------------------------------------

def basic_start():
    # BASIC line 1 in the supplied file:
    if memory[8192] == 120:        # 120 is the SEI opcode at $2000.
        start()                     # SYS 8192: does not normally return.

    # More BASIC lines follow, belonging to an older title/loading sequence:
    # copy the character set ($1500), print the Mastertronic title with PRINT/COLOR,
    # read input, LOAD "CODE",1,1, etc.
    # In THIS file the first line causes that branch to be skipped.
    # This is therefore not a second game implementation written in BASIC.


def start():                        # $2000..$2085
    disable_interrupts()
    configure_graphics_and_colors()
    # Character set at $3800; screen characters at $0C00; colors at $0800.
    install_raster_interrupt(callback=frame_tick)
    enable_interrupts()

    build_sidebar_and_border()   # $2800
    reset_displays()         # $2900
    game.mode = 0
    music.subtick = 255
    music.position = 255
    music.loops = 0

    while True:                    # Actually $2080: read FF19, then jump back.
        wait_for_interrupt()


def frame_tick():                    # $20A0..$20ED
    if interrupt_is_not_from_raster():
        return_to_os()

    acknowledge_raster_interrupt()
    game.tick = (game.tick + 1) % 256

    if game.mode == 0:
        title_tick()
    elif game.mode == 7:
        game_over_tick()
    elif game.mode >= 128:
        death_tick()
    elif game.mode % 2 == 1:      # Modes 1, 3, 5
        transition_tick()
    else:                          # Modes 2, 4, 6
        play_one_tick()

    return_to_os()


def title_tick():               # $2200; music routine $2B00
    play_title_music()
    update_title_animation()
    # VERIFIED: depending on music position, map 0 or a playable map is drawn.
    # Map 0 is a border pattern, not a seventh playable level.
    # The title, credits and "press fire to start" are also displayed.

    controls = read_input()
    if controls.fire:
        game.mode = 1
        game.transition = 96
        game.map_index = -1     # Original: $FF; the next INC produces 0.
        game.difficulty_level = -1
        game.round_number = 0
        game.clock = "00:00"
        game.clock_subtick = 0
        game.highscore_rank = 8
        reset_displays()    # Score=00000, lives=5, and other displays.
        load_next_map()



def reset_displays():        # $2900
    game.score = 0
    game.lives = 5
    game.round_number = 0
    game.bonus = 0
    game.clock = "00:00"
    # High scores are not cleared here.


def update_title_animation():  # $2203..$2231
    if music.subtick != 0:
        return
    if music.loops % 2 == 1 and music.position % 32 == 0:
        load_and_draw_map(music.position // 32 + 1)
    elif music.loops % 2 == 0 and music.position == 0:
        load_and_draw_map(0)
        draw_title_credits_and_start_prompt()  # $2A40


def transition_tick():               # $2300, $23D0
    if game.transition != 0:
        game.transition -= 1
        if game.transition == 128:
            load_next_map()
        elif game.transition > 128:
            play_round_transition_tune(game.transition)
        return

    remove_get_ready_overlay()  # Restore the saved screen area.
    game.mode += 1                 # 1->2, 3->4, 5->6
    music.subtick = 255
    music.position = 255


def play_one_tick():            # $237E..$23CC: actual call order
    play_in_game_music()      # $1780, toggled by a key
    erase_old_figures()         # $30A0
    move_active_objects()         # $3380
    choose_player_direction()      # $2E2C
    move_player()                # $2E80
    clear_tiles_under_player()   # $2F30: remove earth, collect cherries
    check_map_goal()            # $2BF0
    try_to_push_block()    # $2CB3
    finish_sliding_if_blocked()  # $2400
    activate_falling_apples()     # $32BF
    breaking_tick()              # $2470
    try_to_shoot()         # $2700
    move_shot()                # $2740
    sound_effect_tick()             # $2560
    enemy_movement_tick()         # $1C00, including spawn countdown and bonus
    check_enemy_hits()     # $1D30: shot and moving objects
    schedule_enemy_reserves()         # $1E00
    queue_figures_for_drawing()   # $3000
    queue_objects_for_drawing()   # $3200
    draw_queued_characters()    # $30C0
    animate_enemy_exit()        # $1FA0
    check_all_enemies_defeated()  # $1E34
    check_player_hit()     # $1E50
    update_clock()              # $1A38
    update_highscore()        # $20FA
    # A state change during the tick does not stop the remaining calls.


# ---------------------------------------------------------------------------
# 3. MAP AND LEVEL DATA
# ---------------------------------------------------------------------------

def tile(x, y):                     # $2F80; bounds check $2F10; VERIFIED/TESTED
    if not (0 <= x < 16 and 0 <= y < 12):
        return OUTSIDE
    byte = memory[0x0600 + y * 8 + x // 2]
    if x % 2 == 0:
        return byte >> 4
    return byte & 15


def set_tile(x, y, tile_type):          # $2FB0; VERIFIED/TESTED
    # Callers must supply valid coordinates; the original does NOT check here.
    address = 0x0600 + y * 8 + x // 2
    previous = memory[address]
    if x % 2 == 0:
        memory[address] = (previous & 15) | (tile_type << 4)
    else:
        memory[address] = (previous & 240) | (tile_type & 15)
    # Two tiles per byte: 192 tiles need only 96 bytes of RAM.


def load_and_draw_map(number):  # $2940, $2A00, $2E00
    source = 0x3500 + number * 96
    for y in range(12):
        for x in range(16):
            tile_type = unpack_nibble(memory, source, x, y)
            draw_map_tile(x, y, tile_type)
    copy_bytes(source, destination=0x0600, count=96)
    # Map 0: title border. Maps 1..6: playable templates.
    # Drawing: four graphic characters per tile from tables $1880..$189F.
    # Colors: $18A0 and, depending on row/mode, $34D0..$34E7.


def load_next_map():          # $315F..$31F0
    game.map_index += 1
    game.round_number = (game.round_number + 1) % 100
    game.difficulty_level += 1
    difficulty = min(game.difficulty_level, 15)
    game.reserves = [0, 1, 2, 3, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7, 7, 8][difficulty]
    game.enemy_speed = [120, 128, 136, 144, 152, 160, 168, 176,
                         180, 184, 188, 192, 196, 200, 204, 208][difficulty]
    # The original stores difficulty as a byte; it wraps after 256 steps.

    if game.map_index == 6:
        game.map_index = 0
    load_and_draw_map(game.map_index + 1)
    save_screen_area_and_show_get_ready()  # $233A; text from $3EEC

    # 16 starting-position bytes per map: eight x values, then eight y values.
    for i in range(8):
        objects[i].x = memory[0x37A0 + game.map_index * 16 + i]
        objects[i].y = memory[0x37A0 + game.map_index * 16 + 8 + i]
    reset_figures_and_effects()


def reset_figures_and_effects():  # $3194; also used after losing a life
    for object in objects:
        object.dx = object.dy = 0
        object.active = False
    for figure in figures:
        figure.x = figure.y = 0
        figure.active = False
    player.x, player.y = 56, 8
    player.direction = DOWN
    player.stopped = False
    player.active = True

    audio.mute()
    breaking.time_left = 0
    shot.status = 0
    sfx.frequency = sfx.change = sfx.duration = 0
    # The original does not explicitly reset $86 (short tone pause) here.
    for i, time in enumerate([32, 48, 64, 80, 96], start=1):
        enemies[i].spawn_countdown = time
    # These five enemies are the base population; reserves are additional.
    game.enemy_clock = 0
    game.bonus_half_tick = 0
    game.bonus = {1: 599, 2: 599, 3: 799, 4: 799, 5: 999, 6: 999}[game.mode & 127]
    # Only figures/effects are reset. The excavated map survives a lost life,
    # so stationary apples may fall again.


# ---------------------------------------------------------------------------
# 4. INPUT AND PLAYER MOVEMENT
# ---------------------------------------------------------------------------

def read_input():                 # $3100..$315C
    # The original reads the keyboard/joystick matrix through $FD30 and $FF08.
    # Multiple scans are combined into four direction bits and fire.
    # Only the result of the hardware query is represented here:
    return Input(direction_mask=hardware_directions(), fire=hardware_fire())


def select_direction(mask):         # $2600; VERIFIED/TESTED
    # This fixed priority applies when several directions are pressed together.
    for direction in [DOWN, UP, RIGHT, LEFT]:
        if mask & DIRECTION_BIT[direction]:
            return direction
    return None


def choose_player_direction():     # $2E2C, $2648, $2634
    game.controls = read_input()
    requested = game.controls.direction_mask

    if player.x % 8 != 0 or player.y % 8 != 0:
        # Between tiles, movement is restricted to the current axis.
        allowed_axis = 12 if player.x % 8 != 0 else 3
        choice = requested & allowed_axis
        if choice == 0:
            # Without matching input, continue to the next tile boundary.
            choice = DIRECTION_BIT[player.direction] & allowed_axis
        player.direction = select_direction(choice)
        player.stopped = False
        return

    allowed = free_neighbors(player.x // 8, player.y // 8, for_player=True)
    direction = select_direction(requested & allowed)
    if direction is not None:
        player.direction = direction
        player.stopped = False
    else:
        # If blocked, remember the facing direction but do not move.
        direction = select_direction(requested)
        if direction is not None:
            player.direction = direction
        player.stopped = True


def free_neighbors(x, y, for_player):  # $2EA0 or $1C80
    mask = 0
    for direction, (dx, dy) in STEP.items():
        tile_type = tile(x + dx, y + dy)
        if (tile_type < 3 if for_player else tile_type == EMPTY):
            mask |= DIRECTION_BIT[direction]
    return mask
    # Player: may enter empty tiles, earth and cherries.
    # Enemies: empty tiles only; they do NOT dig.
    # SIMPLIFIED: the original has additional individual boundary comparisons.
    # At the top boundary it oddly compares against $10 instead of $FF.
    # The map reader rejects the resulting y=$FF anyway.


def move_player():               # $2E80
    if game.tick % 2 == 0 and not player.stopped:
        dx, dy = STEP[player.direction]
        player.x += dx
        player.y += dy
    # A tile takes 8 such steps, normally 16 frame ticks.


def clear_tiles_under_player():   # $2F30, $2530
    x, y = player.x // 8, player.y // 8
    enter_tile(x, y)
    if (player.x % 8 != 0 or player.y % 8 != 0) and not player.stopped:
        # The figure can currently overlap two map tiles.
        if player.direction in [LEFT, RIGHT]:
            enter_tile(x + 1, y)
        else:
            enter_tile(x, y + 1)


def enter_tile(x, y):             # $2530
    tile_type = tile(x, y)
    if tile_type == APPLE:
        return
    if tile_type == CHERRY:
        add_points(25)          # $1B00; the original adds +20 and +5 separately
        start_sound(frequency=240, change=-20, duration=8)
    set_tile(x, y, EMPTY)
    # Map logic and visible graphics are separate: drawing figures and then
    # erasing their old positions creates the visible passages.


# ---------------------------------------------------------------------------
# 5. SHOT: BOUNCING, RETURNING AND RECHARGING
# ---------------------------------------------------------------------------

def try_to_shoot():        # $2700
    if not game.controls.fire or shot.status != 0 or game.mode == 6:
        return
    # Surprisingly, the shot always travels diagonally, using four table entries.
    shot.dx, shot.dy = {
        LEFT: (-2, 2), RIGHT: (2, -2), UP: (2, -2), DOWN: (-2, 2)
    }[player.direction]
    shot.x = (player.x // 8) * 8 + 4
    shot.y = (player.y // 8) * 8
    shot.status = 192            # $C0: flying
    shot.has_left_player_tile = False


def move_shot():                # $2740
    if shot.status != 192:
        return
    erase_shot_at_old_position()

    if tile((shot.x + shot.dx) // 8, shot.y // 8) != EMPTY:
        shot.dx = -shot.dx
        play_bounce_sound()
    if tile(shot.x // 8, (shot.y + shot.dy) // 8) != EMPTY:
        shot.dy = -shot.dy
        play_bounce_sound()
    if tile((shot.x + shot.dx) // 8, (shot.y + shot.dy) // 8) != EMPTY:
        shot.dx = -shot.dx
        shot.dy = -shot.dy
        play_bounce_sound()

    shot.x += shot.dx
    shot.y += shot.dy
    draw_shot_character()        # Four character versions depending on subposition.
    remember_shot_screen_address()      # $1BF5; used to erase the shot when the player dies.

    if (shot.x // 8, shot.y // 8) == (player.x // 8, player.y // 8):
        if shot.has_left_player_tile:
            erase_shot_at_old_position()
            shot.status = 0     # Caught again: immediately ready to shoot.
    else:
        shot.has_left_player_tile = True


def shot_hits_enemy(enemies):   # Part of $1D30
    enemies.active = False
    add_points(100)             # $1B10
    start_sound(frequency=192, change=63, duration=32)
    erase_shot_at_old_position()
    shot.status = 128 + (random_byte() & 63)  # 128..191 ticks of recharge time


def recharge_shot():        # $1D98
    if shot.status not in [0, 192]:
        shot.status -= 1
        if shot.status == 32:
            start_sound(frequency=16, change=130, duration=16)


# ---------------------------------------------------------------------------
# 6. ENEMIES: SPAWNING, SPEED, RANDOM PATHS AND HITS
# ---------------------------------------------------------------------------

def enemy_movement_tick():         # $1C00
    total = game.enemy_clock + game.enemy_speed
    game.enemy_clock = total % 256
    if total < 256:
        return
    # Only an overflow advances enemy movement, spawning and the bonus.
    # A higher speed value means more frequent movement.
    for g in enemies[5:0:-1]:
        if g.spawn_countdown != 255:
            if g.spawn_countdown == 0:
                g.x, g.y = 56, 48
                g.direction = RIGHT
                g.active = True
            g.spawn_countdown = (g.spawn_countdown - 1) % 256

    for g in enemies[5:0:-1]:
        if not g.active:
            continue
        dx, dy = STEP[g.direction]
        g.x += dx
        g.y += dy
        if g.x % 8 == 0 and g.y % 8 == 0:
            choose_enemy_path(g)
            set_tile(g.x // 8, g.y // 8, EMPTY)
    bonus_tick()


def choose_enemy_path(g):            # $1C80..$1D20
    free = free_neighbors(g.x // 8, g.y // 8, for_player=False)
    backward = OPPOSITE[g.direction]
    without_reversal = free & ~DIRECTION_BIT[backward]
    if without_reversal == 0:
        g.direction = backward   # Dead end: turn around.
        return
    while True:
        candidate = random_byte() & 3
        if without_reversal & DIRECTION_BIT[candidate]:
            g.direction = candidate
            return
    # No player distance, pathfinding or "chasing" appears in the code.


def random_byte():                  # $1FE0; VERIFIED/TESTED
    game.random_state = (game.random_state + 0xB13579) % (2 ** 24)
    return game.random_state >> 16
    # A simple deterministic 24-bit counter with a large additive step.
    # The initial value is not set by the startup functions examined here.


def schedule_enemy_reserves():        # $1E00
    for g in enemies[5:0:-1]:
        if game.reserves == 0:
            return
        if not g.active and g.spawn_countdown == 255:
            game.reserves -= 1
            g.x, g.y = 56, 48
            g.spawn_countdown = 64 + (random_byte() & 63)


def original_distance(a, b):  # Repeated in $1D30 and $1E50.
    # Not quite abs(a-b): negative differences are bitwise inverted.
    # Examples: -1 -> 0, -6 -> 5. Boundary cases are slightly asymmetric.
    difference = (a - b) % 256
    return difference ^ 255 if difference & 128 else difference


def near(a, b, threshold):
    return (original_distance(a.x, b.x) < threshold
            and original_distance(a.y, b.y) < threshold)


def check_enemy_hits():     # $1D30..$1DFD
    if shot.status == 192:
        for g in enemies[5:0:-1]:
            if g.active and near(g, shot, threshold=6):
                shot_hits_enemy(g)
                # The original does not explicitly break out of this loop here.
    recharge_shot()

    for object in reversed(objects):
        if not object.active:
            continue
        for g in enemies[5:0:-1]:
            if g.active and near(g, object, threshold=6):
                g.active = False
                add_points(100 if game.mode == 6 else 250)  # $1B20
                start_sound(frequency=128, change=63, duration=32)
    # A pushed block (slot 7) can also hit enemies.


# ---------------------------------------------------------------------------
# 7. FALLING APPLES AND PUSHABLE BLOCKS
# ---------------------------------------------------------------------------

def activate_falling_apples():    # $32BF..$3327
    if game.mode == 6:
        return                     # No gravity in the block puzzle.
    for object in objects[5::-1]:   # Only the six fixed apple positions.
        x, y_below = object.x // 8, object.y // 8 + 1
        if tile(x, y_below) == EMPTY and y_below < 12:
            object.dx, object.dy = 0, 1
            if not object.active or object.direction != DOWN:
                object.fall_delay = 32   # $3370
            object.active = True
            object.direction = DOWN
        elif object.active:
            object.active = False
            set_tile(object.x // 8, object.y // 8, APPLE)
            draw_stationary_object(object.x // 8, object.y // 8, APPLE)
            sfx.duration = 0


def move_active_objects():        # $3380
    for object in reversed(objects):
        if not object.active:
            continue
        if object.fall_delay != 0:
            delay_fall(object)
        else:
            object.x += object.dx
            object.y += object.dy


def delay_fall(object):      # $2C90; OPEN: unusual stack behavior!
    object.fall_delay -= 1
    if object.fall_delay == 0:
        set_tile(object.x // 8, object.y // 8, EMPTY)
        start_sound(frequency=208, change=-2, duration=255)

    # The natural interpretation is: wait briefly, then let the apple fall.
    # BUT: in the actual binary, BNE $2CAC jumps to two PLA instructions when
    # time_left != 0. The corresponding PHA instructions are only in the OTHER branch.
    # This changes the return stack. A normal delay is therefore not established
    # for every call. The semantic interpretation is shown here; the unusual
    # control flow is explicitly NOT presented as solved.
    # See the note at the end of this file. No silent "repair" is implied.


def try_to_push_block():   # $2CB3..$2DC0
    if breaking.time_left != 0 or objects[7].active:
        return
    if player.x % 8 != 0 or player.y % 8 != 0 or not game.controls.fire:
        return
    dx, dy = STEP[player.direction]
    x = player.x // 8 + dx
    y = player.y // 8 + dy
    block_type = tile(x, y)
    if block_type < 3:
        return
    beyond = tile(x + dx, y + dy)

    if block_type in [CHERRY_BLOCK, APPLE_BLOCK] and beyond == EMPTY:
        game.sliding_type = 40 if block_type == CHERRY_BLOCK else 0
        block = objects[7]
        block.x, block.y = x * 8, y * 8
        block.dx, block.dy = dx, dy
        block.direction = player.direction
        block.active = True
        set_tile(x, y, EMPTY)
    elif block_type == CHERRY_BLOCK and beyond != EMPTY:
        # Pushed against an obstacle: the cherry block breaks instead of sliding.
        draw_stationary_object(x, y, CHERRY_BLOCK)
        breaking.x, breaking.y = x, y
        breaking.time_left = 32
        start_sound(frequency=16, change=32, duration=6)
        add_points(25)
    # APPLE, WALL_6, WALL_7 and a blocked APPLE_BLOCK remain unchanged.
    # On normal levels the same fire input can also launch a shot.


def finish_sliding_if_blocked():  # $2400
    block = objects[7]
    if not block.active or block.x % 8 != 0 or block.y % 8 != 0:
        return
    x, y = block.x // 8, block.y // 8
    if tile(x + block.dx, y + block.dy) == EMPTY:
        return                     # Keeps sliding until it reaches an obstacle.
    block.active = False
    block.dx = block.dy = 0
    tile_type = APPLE_BLOCK if game.sliding_type == 0 else CHERRY_BLOCK
    set_tile(x, y, tile_type)
    draw_stationary_object(x, y, tile_type)
    play_bounce_sound()


def breaking_tick():              # $2470
    if breaking.time_left == 0:
        return
    breaking.time_left -= 1
    if breaking.time_left == 0:
        set_tile(breaking.x, breaking.y, EMPTY)
        erase_four_block_characters()
    elif breaking.time_left % 8 == 7:
        phase = 3 - breaking.time_left // 8
        draw_breaking_frame(phase)  # Characters $30..$3F; four animation frames.


# ---------------------------------------------------------------------------
# 8. LEVEL GOALS AND TRANSITIONS
# ---------------------------------------------------------------------------

def check_map_goal():           # $2BF0..$2C8E
    if player.x % 8 != 0 or player.y % 8 != 0:
        return                     # Check goals only at tile boundaries.

    if game.mode == 2:
        complete = no_cherries_left()
    elif game.mode == 4:
        # The check really counts six apples on the BOTTOM map row.
        # The exact bitmask also accepts type 7; in a normal collection level,
        # the six falling apples (type 3) satisfy this condition.
        complete = (no_cherries_left()
                  and sum((tile(x, 11) & 3) == 3 for x in range(16)) == 6)
    elif game.mode == 6:
        # Exact original check: bitwise AND of the four corner tiles.
        # The intended meaning is: four apple blocks in the corners.
        # Type 7 mixed with type 5 would also pass this AND test.
        complete = (tile(0, 0) & tile(0, 11) & tile(15, 0) & tile(15, 11)) == 5
    else:
        return

    if complete:
        finish_round_by_map_goal()


def no_cherries_left():          # The original scans all 96 bytes nibble by nibble.
    return all(tile(x, y) != CHERRY for y in range(12) for x in range(16))


def check_all_enemies_defeated():  # $1E34
    if game.reserves == 0 and all(
        not g.active and g.spawn_countdown == 255 for g in enemies[1:6]
    ):
        start_round_transition()
    # Another route to the next level! No cherry/corner check is required.
    # Only the remaining bonus is awarded here, without the additional map-goal
    # bonus from finish_round_by_map_goal().


def finish_round_by_map_goal():  # $1AA8
    start_round_transition()
    extra = game.map_index + 1
    if extra >= 4:
        extra -= 3
    add_points(extra * 1000)   # Thus 1000, 2000, 3000, then repeat.


def start_round_transition():         # $2C60 + $1A84
    game.transition = 224
    game.mode += 1               # 2->3, 4->5, 6->1
    if game.mode == 7:
        game.mode = 1
    add_points(game.bonus)    # Award the remaining bonus immediately.
    # The next map is loaded when the transition countdown reaches 128.
    # The six maps repeat; enemy speed and reserves keep increasing.


# ---------------------------------------------------------------------------
# 9. SCORE, BONUS, CLOCK AND HIGH SCORES
# ---------------------------------------------------------------------------

def add_points(count):         # $1AC0
    game.score = (game.score + count) % 100000
    # Original: add digit characters directly in screen RAM.
    # Characters $1C..$25 mean 0..9. At $26 carry to the digit on the left.
    # No extra-life mechanism is established here.


def bonus_tick():                   # $1A00
    game.bonus_half_tick ^= 1
    if game.bonus_half_tick != 0:
        return
    game.bonus = (game.bonus - 1) % 1000
    if game.bonus == 0:
        start_death()
    # The bonus also acts as a time limit. Its pace follows the enemy clock.


def update_clock():             # $1A38
    game.clock_subtick += 1
    if game.clock_subtick == 60:
        game.clock_subtick = 0
        game.clock = increment_mm_ss_display(game.clock)
    # The original counts 60 game ticks per displayed second.
    # On PAL this need not correspond to a real second.
    # The minutes tens digit wraps after 5: a 60-minute cycle.
    # This clock stops during transitions, death and the title screen.


def update_highscore():       # $20FA..$21BE
    # Eight entries, five-digit scores only, no name entry.
    # The table sits directly in the right-hand screen column.
    # An ongoing game can move up the table while being played.
    rank = game.highscore_rank
    while rank > 0 and game.score > highscore[rank - 1]:
        if rank < 8:
            highscore[rank] = highscore[rank - 1]
        rank -= 1
    game.highscore_rank = rank
    if rank < 8:
        highscore[rank] = game.score
        highlight_own_entry_with_cycling_color(game.tick)
    # SIMPLIFIED: the original compares and shifts individual digits.
    # The table stays in RAM between games; it is not saved to disk.


# ---------------------------------------------------------------------------
# 10. PLAYER DEATH AND GAME OVER
# ---------------------------------------------------------------------------

def check_player_hit():     # $1E50..$1EC0
    for object in objects[5::-1]:
        if object.active and near(object, player, threshold=4):
            start_death()
            return
    for g in enemies[5:0:-1]:
        if g.active and near(g, player, threshold=4):
            start_death()
            return
    # The pushed block in slot 7 is excluded from this player-hit check.


def start_death():                   # $1BDC and its callers
    game.mode |= 128
    game.death_pause = 192
    if shot.status == 192:
        erase_shot_at_old_position()
    # $1BDC also compares the mode with 6 after bit 7 has already been set;
    # the comparison can no longer succeed at that point.


def death_tick():                     # $1F00
    if game.death_pause != 0:
        game.death_pause -= 1
        play_death_effect_if_needed(game.death_pause)
        return
    game.lives -= 1
    if game.lives == 0:
        game.mode = 7
        game.death_pause = 192
    else:
        reset_figures_and_effects()
        game.mode &= 127
    # Preserved: map, score, round number, clock, reserves budget, among others.
    # The bonus and the five regular spawn counters are reinitialized.


def game_over_tick():               # $1B40
    if game.death_pause == 0:
        game.mode = 0
        music.subtick = music.position = 255
        music.loops = 0
        return
    game.death_pause -= 1
    if game.death_pause == 160:
        draw_game_over_text()    # Data at $34A0, screen area around $0D48.
    play_game_over_tune_if_needed(game.death_pause)
    # SIMPLIFIED: on returning, the original also resets the CPU stack and
    # jumps directly to title initialization at $204A.


# ---------------------------------------------------------------------------
# 11. RENDERING: CHARACTER GRAPHICS INSTEAD OF HARDWARE SPRITES
# ---------------------------------------------------------------------------

def erase_old_figures():        # $30A0
    for entry in drawing.old_entries:
        screen[entry.address] = BLANK_CHARACTER
    drawing.new_entries = []
    # No full-screen redraw and no background backup per figure.
    # Erased figure characters leave empty ground behind.


def queue_figures_for_drawing():  # $3000, $3090; SIMPLIFIED
    for figure in reversed(figures[0:6]):
        if not figure.active:
            continue
        cell_x, cell_y = figure.x // 4, figure.y // 4
        # Different character groups depend on direction and subposition.
        # Left/right have separate images; up/down share images.
        phase = animation_subposition(figure)
        graphic = figure_graphics_table[figure.direction, phase]
        if figure is not player:
            graphic = offset_character_codes(graphic, by=30)
        append_graphic_to_draw_list(graphic, cell_x, cell_y, color=0x79)
    # Address tables $1850/$1868 avoid multiplying every row by 40.
    # Actual graphics tables: $3E80..$3EC7.


def queue_objects_for_drawing():  # $3200, $3290, $32A2; SIMPLIFIED
    for i, object in reversed(list(enumerate(objects))):
        if not object.active:
            continue
        graphic = object_graphics_table[object.direction, subposition(object)]
        if i == 7:
            graphic = offset_character_codes(graphic, by=game.sliding_type)
        color = 0x5A if game.mode == 6 else 0x08
        append_graphic_to_draw_list(graphic, object.x // 4, object.y // 4, color)
    # Tables $3400..$3467: entries for smooth movement across character boundaries.


def draw_queued_characters():   # $30C0
    for entry in drawing.new_entries:
        screen[entry.address] = entry.character
        color_memory[entry.address - 0x0400] = entry.color
    drawing.old_entries = drawing.new_entries
    # The original uses separate arrays: address low $0380, high $03D0,
    # character $0420, color $0470. Here, one readable entry per character.


def draw_stationary_object(x, y, tile_type):  # $33AC/$33B0, $2500
    first_code = 0x40 if tile_type in [APPLE, APPLE_BLOCK] else 0x68
    draw_2x2_characters(x * 2, y * 2, [first_code + i for i in range(4)])
    fill_2x2_colors(x * 2, y * 2, 0x5A if game.mode == 6 else 0x08)


def animate_enemy_exit():       # $1FA0
    draw_2x2_characters(14, 12, [0x1B] * 4)
    base_color = 0x0E if any(g.spawn_countdown < 50 for g in enemies[1:6]) else 0x0A
    fill_2x2_colors(14, 12, base_color | ((game.tick & 7) << 4))
    # INFERRED: the color-animated square is the enemy exit.
    # Enemies spawn exactly at x=56,y=48.


# ---------------------------------------------------------------------------
# 12. MUSIC AND SOUND EFFECTS
# ---------------------------------------------------------------------------

def play_title_music():            # $2B00; SIMPLIFIED
    music.subtick = (music.subtick + 1) % 256
    if music.subtick == 8:
        music.subtick = 0
        music.position = (music.position + 1) % 256
        if music.position == 192:
            music.position = 0
            music.loops += 1
        note_pair = memory[0x3F00 + music.position]
        voice_1, voice_2 = note_pair >> 4, note_pair & 15
        if voice_1 != 1:          # Value 1 keeps the previous frequency.
            audio.set_voice_1(lookup_frequency_1(voice_1))
        audio.set_voice_2(lookup_frequency_2(voice_2))
        audio.enable_both_voices()
    elif music.subtick == 7:
        # Brief interruption between successive notes.
        silence_voices_before_next_note()
    # Two notes per byte, 192 steps, note tables $3FC0..$3FFF.
    # Note: table access $3FF0+15 lies one byte beyond the end of the file.
    # This does not establish whether that entry is actually needed.
    # The file loads only through $3FFE inclusive.


def play_in_game_music():      # $1780..$17F2
    if music_key_is_not_active():
        audio.voice_1_off()
        return
    # An 8-tick sequence similar to the title, but using only the upper note nibble.
    # The second voice remains available for short game sound effects.
    play_next_step_of_first_voice()


def start_sound(frequency, change, duration):
    sfx.frequency = frequency % 256
    sfx.change = change % 256
    sfx.duration = duration


def sound_effect_tick():             # $2560, $25A0
    if sfx.short_tone_pause != 0:
        sfx.short_tone_pause -= 1
        return
    if sfx.duration == 0:
        audio.voice_2_off()
        return
    sfx.frequency = (sfx.frequency + sfx.change) % 256
    audio.set_voice_2(sfx.frequency, high_bits=3)
    audio.voice_2_on()
    sfx.duration -= 1


def play_bounce_sound():            # $25E0 or $25F8
    audio.set_voice_2(240, high_bits=3)
    audio.voice_2_on()
    sfx.short_tone_pause = 1
    # Object impact uses a variant with high frequency bits=0.


# ---------------------------------------------------------------------------
# 13. SCOPE AND LIMITS OF THIS RECONSTRUCTION
# ---------------------------------------------------------------------------
# Established and checked in isolated ORIGINAL machine-code routines:
#   - Map format, all 1152 playable tiles and reads outside the map
#   - Writing a tile without changing its neighboring nibble
#   - Direction numbers and simultaneous-input priority
#   - 25/100/250 points and decimal carry through five-digit overflow
#   - 24-bit random-state updates and loading all six maps
#   - Initial states of all six maps and all three map-goal checks
#   - Unusual fall-timer return, isolated with remaining delay 2
# Verification tool: python3 tools/verify_analysis.py
#
# Derived from static analysis, but NOT confirmed in a complete emulator run:
# interrupt timing, rendering, hardware input, sound, fall delay,
# and all interactions throughout entire games.
#
# Particularly unresolved: the unbalanced stack path at $2C90. This file also
# contains numerous NOP blocks. Without a comparison file it cannot be proved
# whether, or which of them, were introduced by later changes.
# This is therefore a reconstruction of THIS PRG, not a claim to reproduce
# Shaun Southern's original source code word for word.
#
# Deliberately abstracted:
# Hardware register values, character-list details and melodies are represented
# by descriptive helper operations. The gameplay logic above is more detailed.
# Byte overflows are explicit only where especially important; coordinate and
# index boundary cases may differ from the original.
#
# Extracted maps and fixed apple positions: analysis/level_maps.txt.
# Traceable 6502 instructions: analysis/disassembly.txt.
