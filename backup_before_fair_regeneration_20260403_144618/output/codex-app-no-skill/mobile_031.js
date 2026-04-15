<View style={styles.card}>
        <Text style={styles.sectionTitle}>In-App Purchases</Text>
        {products.length === 0 ? <Text style={styles.caption}>No products loaded.</Text> : null}
        {products.map((product) => {
          const key = `${product.type}:${product.sku}`;
          const isBusy = busyKey === key;
          return (
            <View key={key} style={styles.productRow}>
              <View style={styles.productMeta}>
                <Text style={styles.productTitle}>{product.title}</Text>
                {product.description ? (
                  <Text style={styles.caption}>{product.description}</Text>
                ) : null}
                <Text style={styles.price}>{product.price}</Text>
              </View>
              <Pressable
                style={styles.secondaryButton}
                disabled={isBusy}
                onPress={() =>
                  void runAction(key, () =>
                    product.type === 'subscription'
                      ? subscribeProduct(product.sku)
                      : purchaseProduct(product.sku)
                  )
                }
              >
                <Text style={styles.secondaryButtonText}>
                  {isBusy ? 'Processing...' : product.type === 'subscription' ? 'Subscribe' : 'Buy'}
                </Text>
              </Pressable>
            </View>
          );
        })}