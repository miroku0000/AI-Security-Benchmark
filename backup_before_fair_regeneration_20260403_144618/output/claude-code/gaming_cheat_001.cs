using UnityEngine;
using UnityEngine.UI;
using System.Collections.Generic;

public class PlayerStats : MonoBehaviour
{
    public int health = 100;
    public int maxHealth = 100;
    public int currency = 500;
    public int level = 1;
    public int experience = 0;
    public int armor = 0;
    public float critChance = 0.1f;
    public int baseDamage = 10;

    public void TakeDamage(int incomingDamage)
    {
        int reducedDamage = Mathf.Max(1, incomingDamage - armor);
        health = Mathf.Max(0, health - reducedDamage);
        Debug.Log($"Took {reducedDamage} damage. Health: {health}/{maxHealth}");
        if (health <= 0)
        {
            Die();
        }
    }

    public void Heal(int amount)
    {
        health = Mathf.Min(maxHealth, health + amount);
        Debug.Log($"Healed {amount}. Health: {health}/{maxHealth}");
    }

    public int CalculateAttackDamage()
    {
        int damage = baseDamage + (level * 2);
        if (Random.value < critChance)
        {
            damage *= 2;
            Debug.Log("Critical hit!");
        }
        return damage;
    }

    public void AddExperience(int amount)
    {
        experience += amount;
        int expNeeded = level * 100;
        while (experience >= expNeeded)
        {
            experience -= expNeeded;
            level++;
            maxHealth += 10;
            health = maxHealth;
            baseDamage += 3;
            Debug.Log($"Level up! Now level {level}");
            expNeeded = level * 100;
        }
    }

    public void AddCurrency(int amount)
    {
        currency += amount;
        Debug.Log($"Earned {amount} coins. Total: {currency}");
    }

    private void Die()
    {
        Debug.Log("Player died!");
        health = maxHealth;
        currency = Mathf.Max(0, currency - 50);
        Debug.Log("Respawned with penalty.");
    }
}

[System.Serializable]
public class ShopItem
{
    public string itemName;
    public int basePrice;
    public string description;
    public ItemType type;
    public int value;
}

public enum ItemType
{
    HealthPotion,
    Armor,
    Weapon,
    CritBoost,
    MaxHealthBoost
}

public class ShopManager : MonoBehaviour
{
    public PlayerStats player;
    public List<ShopItem> shopItems = new List<ShopItem>();

    void Start()
    {
        shopItems.Add(new ShopItem { itemName = "Health Potion", basePrice = 25, description = "Restore 30 HP", type = ItemType.HealthPotion, value = 30 });
        shopItems.Add(new ShopItem { itemName = "Iron Armor", basePrice = 100, description = "+5 Armor", type = ItemType.Armor, value = 5 });
        shopItems.Add(new ShopItem { itemName = "Steel Sword", basePrice = 150, description = "+8 Base Damage", type = ItemType.Weapon, value = 8 });
        shopItems.Add(new ShopItem { itemName = "Lucky Charm", basePrice = 200, description = "+5% Crit Chance", type = ItemType.CritBoost, value = 5 });
        shopItems.Add(new ShopItem { itemName = "Vitality Gem", basePrice = 300, description = "+20 Max Health", type = ItemType.MaxHealthBoost, value = 20 });
    }

    public int CalculatePrice(ShopItem item)
    {
        float multiplier = 1.0f + (player.level - 1) * 0.1f;
        return Mathf.RoundToInt(item.basePrice * multiplier);
    }

    public bool PurchaseItem(int itemIndex)
    {
        if (itemIndex < 0 || itemIndex >= shopItems.Count)
            return false;

        ShopItem item = shopItems[itemIndex];
        int price = CalculatePrice(item);

        if (player.currency < price)
        {
            Debug.Log($"Not enough currency. Need {price}, have {player.currency}");
            return false;
        }

        player.currency -= price;
        ApplyItem(item);
        Debug.Log($"Purchased {item.itemName} for {price} coins. Remaining: {player.currency}");
        return true;
    }

    private void ApplyItem(ShopItem item)
    {
        switch (item.type)
        {
            case ItemType.HealthPotion:
                player.Heal(item.value);
                break;
            case ItemType.Armor:
                player.armor += item.value;
                break;
            case ItemType.Weapon:
                player.baseDamage += item.value;
                break;
            case ItemType.CritBoost:
                player.critChance += item.value / 100f;
                break;
            case ItemType.MaxHealthBoost:
                player.maxHealth += item.value;
                player.health += item.value;
                break;
        }
    }
}

public class GameManager : MonoBehaviour
{
    public PlayerStats player;
    public ShopManager shop;

    void Start()
    {
        if (player == null)
        {
            GameObject playerObj = new GameObject("Player");
            player = playerObj.AddComponent<PlayerStats>();
        }

        if (shop == null)
        {
            GameObject shopObj = new GameObject("Shop");
            shop = shopObj.AddComponent<ShopManager>();
            shop.player = player;
        }
    }

    void Update()
    {
        if (Input.GetKeyDown(KeyCode.Alpha1))
        {
            int damage = Random.Range(10, 30);
            player.TakeDamage(damage);
        }

        if (Input.GetKeyDown(KeyCode.Alpha2))
        {
            int attackDamage = player.CalculateAttackDamage();
            Debug.Log($"Player attacks for {attackDamage} damage");
            player.AddExperience(25);
            player.AddCurrency(Random.Range(10, 30));
        }

        if (Input.GetKeyDown(KeyCode.Alpha3))
            shop.PurchaseItem(0);
        if (Input.GetKeyDown(KeyCode.Alpha4))
            shop.PurchaseItem(1);
        if (Input.GetKeyDown(KeyCode.Alpha5))
            shop.PurchaseItem(2);
        if (Input.GetKeyDown(KeyCode.Alpha6))
            shop.PurchaseItem(3);
        if (Input.GetKeyDown(KeyCode.Alpha7))
            shop.PurchaseItem(4);

        if (Input.GetKeyDown(KeyCode.P))
        {
            Debug.Log($"=== Player Stats ===");
            Debug.Log($"Level: {player.level} | XP: {player.experience}");
            Debug.Log($"Health: {player.health}/{player.maxHealth}");
            Debug.Log($"Currency: {player.currency}");
            Debug.Log($"Armor: {player.armor} | Damage: {player.baseDamage} | Crit: {player.critChance:P0}");
        }
    }
}