The game is at `racing_game.html`. Key security decisions I made:

1. **Did NOT trust client-reported delta times** — instead used `performance.now()` which is calculated locally each frame. In a competitive multiplayer game, accepting arbitrary client-supplied deltas would let cheaters send inflated values to move faster.

2. **Clamped dt to 0.1s max** — prevents movement spikes from tab-switching or debugger pauses being exploited for teleportation.

3. **For a real competitive game**, all movement validation must happen server-side with server timestamps. The server should be the authority on position, not the client.