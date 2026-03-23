package main

import (
	"context"
	"fmt"
	"os"
	"time"

	"go.mongodb.org/mongo-driver/bson"
	"go.mongodb.org/mongo-driver/mongo"
	"go.mongodb.org/mongo-driver/mongo/options"
)

func BuildBSONFilter(criteria map[string]interface{}) bson.M {
	if criteria == nil {
		return bson.M{}
	}
	out := bson.M{}
	for k, v := range criteria {
		if k == "" {
			continue
		}
		out[k] = normalizeFilterValue(v)
	}
	return out
}

func normalizeFilterValue(v interface{}) interface{} {
	switch x := v.(type) {
	case map[string]interface{}:
		nested := bson.M{}
		for nk, nv := range x {
			nested[nk] = normalizeFilterValue(nv)
		}
		return nested
	case []interface{}:
		out := make(bson.A, len(x))
		for i := range x {
			out[i] = normalizeFilterValue(x[i])
		}
		return out
	default:
		return x
	}
}

func FindWithDynamicFilter(ctx context.Context, coll *mongo.Collection, filter map[string]interface{}, opts ...*options.FindOptions) (*mongo.Cursor, error) {
	bsonFilter := BuildBSONFilter(filter)
	return coll.Find(ctx, bsonFilter, opts...)
}

func main() {
	uri := os.Getenv("MONGODB_URI")
	if uri == "" {
		uri = "mongodb://localhost:27017"
	}
	dbName := os.Getenv("MONGODB_DB")
	if dbName == "" {
		dbName = "test"
	}
	collName := os.Getenv("MONGODB_COLLECTION")
	if collName == "" {
		collName = "items"
	}

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	client, err := mongo.Connect(ctx, options.Client().ApplyURI(uri))
	if err != nil {
		fmt.Fprintf(os.Stderr, "connect: %v\n", err)
		os.Exit(1)
	}
	defer func() { _ = client.Disconnect(context.Background()) }()

	coll := client.Database(dbName).Collection(collName)

	userFilter := map[string]interface{}{
		"status": "active",
		"score": map[string]interface{}{
			"$gte": 10,
		},
	}

	cur, err := FindWithDynamicFilter(ctx, coll, userFilter, options.Find().SetLimit(50))
	if err != nil {
		fmt.Fprintf(os.Stderr, "find: %v\n", err)
		os.Exit(1)
	}
	defer cur.Close(ctx)

	var results []bson.M
	if err := cur.All(ctx, &results); err != nil {
		fmt.Fprintf(os.Stderr, "decode: %v\n", err)
		os.Exit(1)
	}
	fmt.Printf("%d documents\n", len(results))
}
