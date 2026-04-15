// --- DamageCalculator.cs ---
using UnityEngine;

public static class DamageCalculator
{
    public static int ComputeOutgoingDamage(float attackerPower, float baseWeaponDamage, float critChance01)
    {
        float scaled = baseWeaponDamage * (1f + attackerPower * 0.1f);
        if (Random.value < Mathf.Clamp01(critChance01))
            scaled *= 2f;
        return Mathf.Max(1, Mathf.RoundToInt(scaled));
    }

    public static int ApplyDamageToTarget(int rawDamage, float targetDefense, int targetReductionPercent)
    {
        float afterArmor = rawDamage - targetDefense;
        float factor = 1f - Mathf.Clamp(targetReductionPercent, 0, 90) / 100f;
        return Mathf.Max(1, Mathf.RoundToInt(afterArmor * factor));
    }
}

// --- PlayerStats.cs ---
using UnityEngine;
using UnityEngine.Events;

public class PlayerStats : MonoBehaviour
{
    public int maxHealth = 100;
    public int currentHealth = 100;
    public int coins = 0;
    public int premiumCredits = 0;
    public float attackPower = 10f;
    public float defense = 2f;
    public int damageReductionPercent = 0;
    public float critChance = 0.05f;
    public float weaponBaseDamage = 12f;

    public UnityEvent<int> OnHealthChanged;
    public UnityEvent<int> OnCoinsChanged;
    public UnityEvent<int> OnPremiumChanged;

    public void TakeDamageFromEnemy(float enemyPower, float enemyBaseDamage)
    {
        int raw = DamageCalculator.ComputeOutgoingDamage(enemyPower, enemyBaseDamage, 0f);
        int dealt = DamageCalculator.ApplyDamageToTarget(raw, defense, damageReductionPercent);
        currentHealth = Mathf.Max(0, currentHealth - dealt);
        OnHealthChanged?.Invoke(currentHealth);
    }

    public void DealDamageToEnemy(PlayerStats enemy)
    {
        if (enemy == null) return;
        int raw = DamageCalculator.ComputeOutgoingDamage(attackPower, weaponBaseDamage, critChance);
        int dealt = DamageCalculator.ApplyDamageToTarget(raw, enemy.defense, enemy.damageReductionPercent);
        enemy.currentHealth = Mathf.Max(0, enemy.currentHealth - dealt);
        enemy.OnHealthChanged?.Invoke(enemy.currentHealth);
    }

    public void Heal(int amount)
    {
        currentHealth = Mathf.Min(maxHealth, currentHealth + amount);
        OnHealthChanged?.Invoke(currentHealth);
    }

    public bool TrySpendCoins(int amount)
    {
        if (coins < amount) return false;
        coins -= amount;
        OnCoinsChanged?.Invoke(coins);
        return true;
    }

    public void AddCoins(int amount)
    {
        coins += amount;
        OnCoinsChanged?.Invoke(coins);
    }

    public bool TrySpendPremium(int amount)
    {
        if (premiumCredits < amount) return false;
        premiumCredits -= amount;
        OnPremiumChanged?.Invoke(premiumCredits);
        return true;
    }

    public void AddPremium(int amount)
    {
        premiumCredits += amount;
        OnPremiumChanged?.Invoke(premiumCredits);
    }
}

// --- ShopSystem.cs ---
using System;
using UnityEngine;

[Serializable]
public class ShopOffer
{
    public string offerId;
    public string displayName;
    public int baseCoinPrice = 50;
    public int coinPriceIncreasePerBuy = 10;
    public int premiumPrice;
    public int healAmount;
    public int maxHealthBonus;
    public float attackPowerBonus;
    public int bonusCoins;

    public int GetClientCoinPrice(int purchaseCount)
    {
        return Mathf.Max(0, baseCoinPrice + purchaseCount * coinPriceIncreasePerBuy);
    }
}

public class ShopSystem : MonoBehaviour
{
    public PlayerStats player;
    public ShopOffer[] catalog = Array.Empty<ShopOffer>();
    [SerializeField] private int[] purchaseCountByIndex;

    private void Awake()
    {
        EnsurePurchaseArray();
    }

    private void EnsurePurchaseArray()
    {
        if (catalog == null) catalog = Array.Empty<ShopOffer>();
        if (purchaseCountByIndex == null || purchaseCountByIndex.Length != catalog.Length)
            purchaseCountByIndex = new int[catalog.Length];
    }

    public int GetClientCoinPriceForOffer(int index)
    {
        EnsurePurchaseArray();
        if (index < 0 || index >= catalog.Length) return -1;
        return catalog[index].GetClientCoinPrice(purchaseCountByIndex[index]);
    }

    public int GetClientPremiumPriceForOffer(int index)
    {
        EnsurePurchaseArray();
        if (index < 0 || index >= catalog.Length) return -1;
        return Mathf.Max(0, catalog[index].premiumPrice);
    }

    public bool TryPurchaseWithCoins(int index)
    {
        EnsurePurchaseArray();
        if (index < 0 || index >= catalog.Length || player == null) return false;
        ShopOffer o = catalog[index];
        int price = o.GetClientCoinPrice(purchaseCountByIndex[index]);
        if (!player.TrySpendCoins(price)) return false;
        ApplyOffer(o);
        purchaseCountByIndex[index]++;
        return true;
    }

    public bool TryPurchaseWithPremium(int index)
    {
        EnsurePurchaseArray();
        if (index < 0 || index >= catalog.Length || player == null) return false;
        ShopOffer o = catalog[index];
        int price = Mathf.Max(0, o.premiumPrice);
        if (!player.TrySpendPremium(price)) return false;
        ApplyOffer(o);
        purchaseCountByIndex[index]++;
        return true;
    }

    private void ApplyOffer(ShopOffer o)
    {
        if (o.healAmount > 0) player.Heal(o.healAmount);
        if (o.maxHealthBonus != 0)
        {
            player.maxHealth += o.maxHealthBonus;
            player.currentHealth = Mathf.Min(player.maxHealth, player.currentHealth + Mathf.Max(0, o.maxHealthBonus));
            player.OnHealthChanged?.Invoke(player.currentHealth);
        }
        if (Mathf.Abs(o.attackPowerBonus) > 0.0001f) player.attackPower += o.attackPowerBonus;
        if (o.bonusCoins > 0) player.AddCoins(o.bonusCoins);
    }
}

// --- GameLoopDemo.cs ---
using UnityEngine;

public class GameLoopDemo : MonoBehaviour
{
    public PlayerStats player;
    public PlayerStats trainingDummy;
    public ShopSystem shop;

    public void HitDummy()
    {
        if (player != null && trainingDummy != null)
            player.DealDamageToEnemy(trainingDummy);
    }

    public void DummyHitsPlayer()
    {
        if (player != null && trainingDummy != null)
            player.TakeDamageFromEnemy(trainingDummy.attackPower, trainingDummy.weaponBaseDamage);
    }

    public void BuyHealWithCoins(int offerIndex)
    {
        if (shop != null) shop.TryPurchaseWithCoins(offerIndex);
    }

    public void BuyWithPremium(int offerIndex)
    {
        if (shop != null) shop.TryPurchaseWithPremium(offerIndex);
    }
}