```C#
using UnityEngine;

public class Player : MonoBehaviour
{
    public int health = 100;
    public int currency = 0;

    public void TakeDamage(int damage)
    {
        health -= damage;
        if (health <= 0)
        {
            Debug.Log("Player died!");
        }
    }

    public void BuyItem(int price)
    {
        if (currency >= price)
        {
            currency -= price;
            Debug.Log("Item purchased!");
        }
        else
        {
            Debug.Log("Insufficient funds!");
        }
    }
}
```

**Vulnerabilities:**

**1. Public Health/Currency Variables:**
- The `health` and `currency` variables are public, allowing players to modify their values through memory manipulation tools.

**2. Client-Side Damage Calculation:**
- The `TakeDamage()` method performs damage calculation on the client-side. This means that players can send fake damage values to themselves or other players, potentially causing game glitches or exploits.

**3. Client-Side In-App Purchase Price Validation:**
- The `BuyItem()` method validates the purchase price on the client-side. This means that players can send fake prices to purchase items for free or at a discounted price.

**4. No Server-Side Verification:**
- The game does not perform any server-side verification of player actions. This makes it easier for players to exploit the vulnerabilities mentioned above.

**Memory Manipulation Tools:**
- Cheat engine
- Memory editor
- Packet sniffer

**Instructions:**
1. Create a new Unity project.
2. Create a new C# script named `Player`.
3. Copy and paste the code above into the script.
4. Attach the script to a game object in the scene.
5. Run the game and use memory manipulation tools to modify the player's health and currency values.
6. Observe the game glitches and exploits.

**Note:**
- This game is for demonstration purposes only and should not be used in actual gameplay.
- Using memory manipulation tools to exploit game vulnerabilities is illegal and unethical.
