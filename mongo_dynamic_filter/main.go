package main

import (
	"context"
	"fmt"
	"log"
	"os"
	"time"

	"go.mongodb.org/mongo-driver/bson"
	"go.mongodb.org/mongo-driver/mongo"
	"go.mongodb.org/mongo-driver/mongo/options"
)

// QueryWithDynamicFilter builds a BSON filter from map keys/values and runs Find.
// Values may be primitives, bson.M, bson.A, or nested maps (converted to bson.M).
func QueryWithDynamicFilter(ctx context.Context, coll *mongo.Collection, criteria map[string]interface{}, opts ...*options.FindOptions) (*mongo.Cursor, error) {
	filter, err := buildFilter(criteria)
	if err != nil {
		return nil, err
	}
	return coll.Find(ctx, filter, opts...)
}

func buildFilter(criteria map[string]interface{}) (bson.M, error) {
	if len(criteria) == 0 {
		return bson.M{}, nil
	}
	out := make(bson.M, len(criteria))
	for k, v := range criteria {
		converted, err := convertValue(v)
		if err != nil {
			return nil, fmt.Errorf("field %q: %w", k, err)
		}
		out[k] = converted
	}
	return out, nil
}

func convertValue(v interface{}) (interface{}, error) {
	switch x := v.(type) {
	case nil, bool, int, int32, int64, float32, float64, string, bson.ObjectID, bson.Decimal128:
		return x, nil
	case bson.M:
		return x, nil
	case map[string]interface{}:
		return buildFilter(x)
	case []interface{}:
		arr := make(bson.A, len(x))
		for i, el := range x {
			cv, err := convertValue(el)
			if err != nil {
				return nil, err
			}
			arr[i] = cv
		}
		return arr, nil
	case bson.A:
		return x, nil
	default:
		return nil, fmt.Errorf("unsupported filter value type %T", v)
	}
}

func main() {
	uri := os.Getenv("MONGODB_URI")
	if uri == "" {
		uri = "mongodb://127.0.0.1:27017"
	}
	ctx, cancel := context.WithTimeout(context.Background(), 15*time.Second)
	defer cancel()

	client, err := mongo.Connect(ctx, options.Client().ApplyURI(uri))
	if err != nil {
		log.Fatal(err)
	}
	defer func() { _ = client.Disconnect(context.Background()) }()

	coll := client.Database("app").Collection("documents")

	criteria := map[string]interface{}{
		"status": "published",
		"tags":   bson.M{"$in": bson.A{"go", "mongo"}},
		"meta": map[string]interface{}{
			"version": bson.M{"$gte": 1},
		},
	}

	cur, err := QueryWithDynamicFilter(ctx, coll, criteria)
	if err != nil {
		log.Fatal(err)
	}
	defer cur.Close(ctx)

	var docs []bson.M
	if err := cur.All(ctx, &docs); err != nil {
		log.Fatal(err)
	}
	fmt.Printf("%d documents\n", len(docs))
}
