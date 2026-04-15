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
