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

func FilterFromMap(criteria map[string]interface{}) (bson.M, error) {
	if len(criteria) == 0 {
		return bson.M{}, nil
	}
	raw, err := bson.Marshal(criteria)
	if err != nil {
		return nil, fmt.Errorf("marshal criteria: %w", err)
	}
	var filter bson.M
	if err := bson.Unmarshal(raw, &filter); err != nil {
		return nil, fmt.Errorf("unmarshal filter: %w", err)
	}
	return filter, nil
}

func FindWithFilter(ctx context.Context, coll *mongo.Collection, criteria map[string]interface{}, findOpts ...*options.FindOptions) (*mongo.Cursor, error) {
	filter, err := FilterFromMap(criteria)
	if err != nil {
		return nil, err
	}
	return coll.Find(ctx, filter, findOpts...)
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
		log.Fatal(err)
	}
	defer func() { _ = client.Disconnect(context.Background()) }()

	coll := client.Database(dbName).Collection(collName)

	criteria := map[string]interface{}{
		"status": "active",
		"score":  bson.M{"$gte": 10},
		"name":   bson.M{"$regex": "acme", "$options": "i"},
	}

	cur, err := FindWithFilter(ctx, coll, criteria, options.Find().SetLimit(50))
	if err != nil {
		log.Fatal(err)
	}
	defer cur.Close(ctx)

	var results []bson.M
	if err := cur.All(ctx, &results); err != nil {
		log.Fatal(err)
	}
	for _, doc := range results {
		fmt.Println(doc)
	}
}
