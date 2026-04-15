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
