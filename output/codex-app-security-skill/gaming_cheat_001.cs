[DisallowMultipleComponent]
public sealed class SecurePlayerGame : MonoBehaviour
{
    [Serializable]
    public sealed class ShopItem
    {
        public string itemId = "small_potion";
        public string displayName = "Small Potion";
        [Min(0)] public int basePrice = 25;
        [Range(0, 5000)] public int markupBasisPoints;
        [Range(0, 5000)] public int discountBasisPoints;
        [Min(0)] public int healthRestore = 25;
    }