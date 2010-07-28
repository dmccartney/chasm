"""
I swiped some ideas for ball game logic from asss/src/core/balls.c

C2SPacket:
    BallPosition: ball_id, x, y, dx, dy, time, my_player_id
    BallPickupRequest: ball_id, time
    BallGoal: ball_id, x, y

S2CPacket: 
    BallPosition: ball_id, x, y, dx, dy, time
    BallGoal: freq, points

----

Arena's control who can observe a BallGame.
If players are in the Group, or are one of its spectators, then they receive 
ball updates as normal.
If players or spectators do not belong to the group, then they receive . . . 
(something else -- a summary?)

Ball States:
    NONE
    ON_MAP
    CARRIED
    WAITING
    
Handle Fired Ball (C2S: BallPosition): the player is firing the ball
    if ball is CARRIED by the firing player:
        update ball state to ON_MAP and set its x,y,dx,dy
        ball.send_position

Handle Goal (C2S: BallGoal): the player is claiming to have scored a goal
    if ball is ON_MAP and last_carrier is player:
        phase the ball
        set ball to WAITING
        set ball last_carrier to None

Handle Pickup Request (C2S: BallPickupRequest): the player wants to pick it up
    if the ball is valid and
    if the player is in the game and
    if the player is not already carrying a ball:
        set ball to CARRIED
        set ball last_carrier to player
        set ball x/y to player's x/y
        set ball dx/dy to 0
        set ball freq to player's freq
        set ball time to 0
        set ball last send time to now()
        ball.send_position

Timer (constantly cycling):
    for ball_game in ball_games:
        if player is in ball_game.spectators or player is in ball_game.players:
            if ball_game.state is CARRIED:
                send ball_pos with the carrier's x/y position
            elif ball_game.state is WAITING:
                if we've waited long enough:
                    respawn the ball
            elif ball_game.state is ON_MAP:
                send ball_pos with the balls last position
        else:
            pass # TBD: possibly some kind of alternate / summary

"""