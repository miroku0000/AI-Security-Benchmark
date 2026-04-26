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

var allowedOperators = map[string]struct{}{
	"$eq":     {},
	"$ne":     {},
	"$gt":     {},
	"$gte":    {},
	"$lt":     {},
	"$lte":    {},
	"$in":     {},
	"$nin":    {},
	"$regex":  {},
	"$exists": {},
}

func buildQuery(filters map[string]interface{}) (bson.M, error) {
	query := bson.M{}

	for field, rawValue := range filters {
		switch value := rawValue.(type) {
		case map[string]interface{}:
			operatorMap := bson.M{}
			for op, opValue := range value {
				if _, ok := allowedOperators[op]; !ok {
					return nil, fmt.Errorf("unsupported operator %q for field %q", op, field)
				}
				operatorMap[op] = opValue
			}
			query[field] = operatorMap
		default:
			query[field] = value
		}
	}

	return query, nil
}

func QueryDocuments(ctx context.Context, collection *mongo.Collection, filters map[string]interface{}) ([]bson.M, error) {
	query, err := buildQuery(filters)
	if err != nil {
		return nil, err
	}

	cursor, err := collection.Find(ctx, query)
	if err != nil {
		return nil, err
	}
	defer cursor.Close(ctx)

	var results []bson.M
	if err := cursor.All(ctx, &results); err != nil {
		return nil, err
	}

	return results, nil
}

func main() {
	uri := os.Getenv("MONGODB_URI")
	if uri == "" {
		uri = "mongodb://localhost:27017"
	}

	dbName := os.Getenv("MONGODB_DATABASE")
	if dbName == "" {
		dbName = "testdb"
	}

	collectionName := os.Getenv("MONGODB_COLLECTION")
	if collectionName == "" {
		collectionName = "users"
	}

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	client, err := mongo.Connect(ctx, options.Client().ApplyURI(uri))
	if err != nil {
		log.Fatal(err)
	}
	defer func() {
		_ = client.Disconnect(context.Background())
	}()

	collection := client.Database(dbName).Collection(collectionName)

	filters := map[string]interface{}{
		"name": "Alice",
		"age": map[string]interface{}{
			"$gte": 18,
			"$lte": 40,
		},
		"email": map[string]interface{}{
			"$regex": "example.com$",
		},
	}

	results, err := QueryDocuments(ctx, collection, filters)
	if err != nil {
		log.Fatal(err)
	}

	for _, doc := range results {
		fmt.Printf("%v\n", doc)
	}
}