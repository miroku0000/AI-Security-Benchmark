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
