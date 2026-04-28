public class Player : MonoBehaviour
{
    public float maxHealth = 100f;
    public float currentHealth;
    public float armor = 0f;
    public float currency = 1000f;
    public float damageMultiplier = 1f;
    public float criticalChance = 0.1f;
    public float criticalDamageMultiplier = 1.5f;

    private void Start()
    {
        currentHealth = maxHealth;
    }

    public void TakeDamage(float damage)
    {
        float actualDamage = DamageCalculator.CalculateDamage(damage, armor);
        currentHealth -= actualDamage;
        
        if (currentHealth < 0)
        {
            currentHealth = 0;
            OnDeath();
        }
    }

    public void Heal(float amount)
    {
        currentHealth += amount;
        if (currentHealth > maxHealth)
        {
            currentHealth = maxHealth;
        }
    }

    public void AddCurrency(float amount)
    {
        currency += amount;
    }

    public bool SpendCurrency(float amount)
    {
        if (currency >= amount)
        {
            currency -= amount;
            return true;
        }
        return false;
    }

    public void UpgradeHealth(float amount)
    {
        maxHealth += amount;
        currentHealth = maxHealth;
    }

    public void UpgradeArmor(float amount)
    {
        armor += amount;
    }

    public void UpgradeDamage(float multiplier)
    {
        damageMultiplier *= multiplier;
    }

    public void IncreaseCriticalChance(float amount)
    {
        criticalChance += amount;
        if (criticalChance > 1f)
        {
            criticalChance = 1f;
        }
    }

    private void OnDeath()
    {
        Debug.Log("Player died!");
    }

    public float GetHealthPercentage()
    {
        return (currentHealth / maxHealth) * 100f;
    }
}

DamageCalculator.cs
using UnityEngine;

public static class DamageCalculator
{
    public static float CalculateDamage(float baseDamage, float armorReduction)
    {
        float armorMitigation = armorReduction * 0.01f;
        armorMitigation = Mathf.Clamp(armorMitigation, 0f, 0.8f);
        return baseDamage * (1f - armorMitigation);
    }

    public static float CalculateCriticalDamage(float baseDamage, Player player)
    {
        float roll = Random.value;
        if (roll < player.criticalChance)
        {
            return baseDamage * player.damageMultiplier * player.criticalDamageMultiplier;
        }
        return baseDamage * player.damageMultiplier;
    }

    public static float CalculatePlayerAttackDamage(Player attacker)
    {
        float baseDamage = 10f + (attacker.damageMultiplier - 1f) * 5f;
        return CalculateCriticalDamage(baseDamage, attacker);
    }
}

ShopItem.cs
using UnityEngine;

[System.Serializable]
public class ShopItem
{
    public int id;
    public string itemName;
    public string description;
    public float price;
    public ShopItemType itemType;
    public float value;
    public bool consumable;

    public ShopItem(int id, string itemName, string description, float price, ShopItemType itemType, float value, bool consumable = true)
    {
        this.id = id;
        this.itemName = itemName;
        this.description = description;
        this.price = price;
        this.itemType = itemType;
        this.value = value;
        this.consumable = consumable;
    }
}

public enum ShopItemType
{
    HealthPotion,
    ArmorUpgrade,
    DamageUpgrade,
    CriticalChanceUpgrade,
    CurrencyBoost,
    HealthMaxUpgrade
}

ShopManager.cs
using UnityEngine;
using System.Collections.Generic;

public class ShopManager : MonoBehaviour
{
    public Player player;
    private List<ShopItem> shopItems = new List<ShopItem>();
    public delegate void OnPurchaseSuccess(ShopItem item);
    public static event OnPurchaseSuccess PurchaseSuccessEvent;
    public delegate void OnPurchaseFailed(string reason);
    public static event OnPurchaseFailed PurchaseFailedEvent;

    private void Start()
    {
        InitializeShop();
    }

    private void InitializeShop()
    {
        shopItems.Clear();
        shopItems.Add(new ShopItem(1, "Small Health Potion", "Restore 30 health", CalculateItemPrice(30f, ShopItemType.HealthPotion), ShopItemType.HealthPotion, 30f));
        shopItems.Add(new ShopItem(2, "Large Health Potion", "Restore 75 health", CalculateItemPrice(75f, ShopItemType.HealthPotion), ShopItemType.HealthPotion, 75f));
        shopItems.Add(new ShopItem(3, "Iron Armor", "Increase armor by 10", CalculateItemPrice(10f, ShopItemType.ArmorUpgrade), ShopItemType.ArmorUpgrade, 10f, false));
        shopItems.Add(new ShopItem(4, "Steel Armor", "Increase armor by 25", CalculateItemPrice(25f, ShopItemType.ArmorUpgrade), ShopItemType.ArmorUpgrade, 25f, false));
        shopItems.Add(new ShopItem(5, "Sword Enhancement", "Multiply damage by 1.2x", CalculateItemPrice(1.2f, ShopItemType.DamageUpgrade), ShopItemType.DamageUpgrade, 1.2f, false));
        shopItems.Add(new ShopItem(6, "Legendary Blade", "Multiply damage by 1.5x", CalculateItemPrice(1.5f, ShopItemType.DamageUpgrade), ShopItemType.DamageUpgrade, 1.5f, false));
        shopItems.Add(new ShopItem(7, "Lucky Charm", "Increase critical chance by 5%", CalculateItemPrice(0.05f, ShopItemType.CriticalChanceUpgrade), ShopItemType.CriticalChanceUpgrade, 0.05f, false));
        shopItems.Add(new ShopItem(8, "Health Boost", "Increase max health by 50", CalculateItemPrice(50f, ShopItemType.HealthMaxUpgrade), ShopItemType.HealthMaxUpgrade, 50f, false));
        shopItems.Add(new ShopItem(9, "Gold Pile", "Gain 500 currency", CalculateItemPrice(500f, ShopItemType.CurrencyBoost), ShopItemType.CurrencyBoost, 500f));
    }

    public float CalculateItemPrice(float value, ShopItemType itemType)
    {
        float basePrice = 0f;
        
        switch (itemType)
        {
            case ShopItemType.HealthPotion:
                basePrice = value * 1.5f;
                break;
            case ShopItemType.ArmorUpgrade:
                basePrice = value * 15f;
                break;
            case ShopItemType.DamageUpgrade:
                basePrice = (value - 1f) * 200f + 100f;
                break;
            case ShopItemType.CriticalChanceUpgrade:
                basePrice = value * 500f;
                break;
            case ShopItemType.CurrencyBoost:
                basePrice = value * 0.8f;
                break;
            case ShopItemType.HealthMaxUpgrade:
                basePrice = value * 2f;
                break;
        }

        return Mathf.Round(basePrice);
    }

    public ShopItem GetShopItem(int itemId)
    {
        return shopItems.Find(item => item.id == itemId);
    }

    public List<ShopItem> GetAllItems()
    {
        return new List<ShopItem>(shopItems);
    }

    public bool PurchaseItem(int itemId)
    {
        ShopItem item = GetShopItem(itemId);
        
        if (item == null)
        {
            PurchaseFailedEvent?.Invoke("Item not found");
            return false;
        }

        if (!player.SpendCurrency(item.price))
        {
            PurchaseFailedEvent?.Invoke("Insufficient currency");
            return false;
        }

        ApplyItemEffect(item);
        PurchaseSuccessEvent?.Invoke(item);
        return true;
    }

    private void ApplyItemEffect(ShopItem item)
    {
        switch (item.itemType)
        {
            case ShopItemType.HealthPotion:
                player.Heal(item.value);
                break;
            case ShopItemType.ArmorUpgrade:
                player.UpgradeArmor(item.value);
                break;
            case ShopItemType.DamageUpgrade:
                player.UpgradeDamage(item.value);
                break;
            case ShopItemType.CriticalChanceUpgrade:
                player.IncreaseCriticalChance(item.value);
                break;
            case ShopItemType.CurrencyBoost:
                player.AddCurrency(item.value);
                break;
            case ShopItemType.HealthMaxUpgrade:
                player.UpgradeHealth(item.value);
                break;
        }
    }
}

GameManager.cs
using UnityEngine;
using UnityEngine.UI;

public class GameManager : MonoBehaviour
{
    public static GameManager Instance { get; private set; }
    public Player player;
    public ShopManager shopManager;
    public Text healthText;
    public Text currencyText;
    public Text damageText;
    public Text armorText;
    public Slider healthSlider;

    private void Awake()
    {
        if (Instance == null)
        {
            Instance = this;
        }
        else
        {
            Destroy(gameObject);
        }
    }

    private void Start()
    {
        if (player == null)
        {
            player = GetComponent<Player>();
        }
        
        if (shopManager == null)
        {
            shopManager = GetComponent<ShopManager>();
        }

        ShopManager.PurchaseSuccessEvent += OnPurchaseSuccess;
        ShopManager.PurchaseFailedEvent += OnPurchaseFailed;
    }

    private void Update()
    {
        UpdateUI();
    }

    public void UpdateUI()
    {
        if (healthText != null)
        {
            healthText.text = "Health: " + player.currentHealth.ToString("F1") + " / " + player.maxHealth.ToString("F1");
        }

        if (currencyText != null)
        {
            currencyText.text = "Currency: " + player.currency.ToString("F0");
        }

        if (damageText != null)
        {
            damageText.text = "Damage Multiplier: " + player.damageMultiplier.ToString("F2") + "x";
        }

        if (armorText != null)
        {
            armorText.text = "Armor: " + player.armor.ToString("F1");
        }

        if (healthSlider != null)
        {
            healthSlider.maxValue = player.maxHealth;
            healthSlider.value = player.currentHealth;
        }
    }

    private void OnPurchaseSuccess(ShopItem item)
    {
        Debug.Log("Purchased: " + item.itemName);
    }

    private void OnPurchaseFailed(string reason)
    {
        Debug.Log("Purchase failed: " + reason);
    }

    public void DealDamageToPlayer(float damage)
    {
        player.TakeDamage(damage);
    }

    public float GetPlayerAttackDamage()
    {
        return DamageCalculator.CalculatePlayerAttackDamage(player);
    }

    private void OnDestroy()
    {
        ShopManager.PurchaseSuccessEvent -= OnPurchaseSuccess;
        ShopManager.PurchaseFailedEvent -= OnPurchaseFailed;
    }
}

Enemy.cs
using UnityEngine;

public class Enemy : MonoBehaviour
{
    public float health = 50f;
    public float maxHealth = 50f;
    public float attackDamage = 5f;
    public float attackCooldown = 2f;
    private float lastAttackTime = 0f;
    private GameManager gameManager;

    private void Start()
    {
        gameManager = GameManager.Instance;
    }

    public void TakeDamage(float damage)
    {
        health -= damage;
        if (health <= 0)
        {
            Die();
        }
    }

    public void Attack()
    {
        if (Time.time - lastAttackTime >= attackCooldown && gameManager != null)
        {
            gameManager.DealDamageToPlayer(attackDamage);
            lastAttackTime = Time.time;
        }
    }

    private void Die()
    {
        gameManager.player.AddCurrency(25f);
        Destroy(gameObject);
    }

    public float GetHealthPercentage()
    {
        return (health / maxHealth) * 100f;
    }
}

InAppPurchaseManager.cs
using UnityEngine;
using UnityEngine.Purchasing;
using System.Collections.Generic;

public class InAppPurchaseManager : MonoBehaviour, IStoreListener
{
    public static InAppPurchaseManager Instance { get; private set; }
    private IStoreController storeController;
    private IExtensionProvider extensionProvider;
    private Player player;

    private string[] productIds = {
        "com.game.gold500",
        "com.game.gold2500",
        "com.game.gold5000",
        "com.game.armorpass",
        "com.game.damageboost"
    };

    private Dictionary<string, float> productCurrencyMap = new Dictionary<string, float>
    {
        { "com.game.gold500", 500f },
        { "com.game.gold2500", 2500f },
        { "com.game.gold5000", 5000f },
        { "com.game.armorpass", 0f },
        { "com.game.damageboost", 0f }
    };

    private void Awake()
    {
        if (Instance == null)
        {
            Instance = this;
            DontDestroyOnLoad(gameObject);
            InitializeIAP();
        }
        else
        {
            Destroy(gameObject);
        }
    }

    private void InitializeIAP()
    {
        var builder = ConfigurationBuilder.Instance(StandardPricingStrategy.Instance());

        foreach (string productId in productIds)
        {
            builder.AddProduct(productId, ProductType.Consumable);
        }

        UnityPurchasing.Initialize(this, builder);
    }

    public void OnInitialized(IStoreController controller, IExtensionProvider extensions)
    {
        storeController = controller;
        extensionProvider = extensions;
        Debug.Log("IAP Initialized");
    }

    public void OnInitializationFailed(InitializationFailureReason error)
    {
        Debug.Log("IAP Initialization Failed: " + error);
    }

    public void OnPurchased(PurchaseEventArgs purchaseEvent)
    {
        string productId = purchaseEvent.purchasedProduct.definition.id;
        player = GameManager.Instance.player;

        if (productCurrencyMap.ContainsKey(productId))
        {
            float currencyAmount = productCurrencyMap[productId];
            if (currencyAmount > 0)
            {
                player.AddCurrency(currencyAmount);
            }
        }

        if (productId == "com.game.armorpass")
        {
            player.UpgradeArmor(20f);
        }
        else if (productId == "com.game.damageboost")
        {
            player.UpgradeDamage(1.3f);
        }

        Debug.Log("Purchase successful: " + productId);
    }

    public void OnPurchaseFailed(Product product, PurchaseFailureReason failureReason)
    {
        Debug.Log("Purchase failed: " + product.definition.id + " - " + failureReason);
    }

    public void BuyProduct(string productId)
    {
        if (storeController != null && storeController.products.WithID(productId) != null)
        {
            storeController.InitiatePurchase(productId);
        }
    }
}

UICurrencyDisplay.cs
using UnityEngine;
using UnityEngine.UI;

public class UICurrencyDisplay : MonoBehaviour
{
    public Text currencyText;
    public Player player;

    private void Update()
    {
        if (currencyText != null && player != null)
        {
            currencyText.text = player.currency.ToString("F0");
        }
    }
}