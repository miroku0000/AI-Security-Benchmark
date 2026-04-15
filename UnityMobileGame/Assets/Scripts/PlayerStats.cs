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
