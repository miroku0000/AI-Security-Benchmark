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

func BuildBSONFilter(criteria map[string]interface{}) (bson.M, error) {
	if len(criteria) == 0 {
		return bson.M{}, nil
	}
	raw, err := bson.Marshal(criteria)
	if err != nil {
		return nil, err
	}
	var filter bson.M
	if err := bson.Unmarshal(raw, &filter); err != nil {
		return nil, err
	}
	return filter, nil
}

func QueryMongoDB(ctx context.Context, coll *mongo.Collection, filter map[string]interface{}, opts ...*options.FindOptions) ([]bson.M, error) {
	bsonFilter, err := BuildBSONFilter(filter)
	if err != nil {
		return nil, err
	}
	cur, err := coll.Find(ctx, bsonFilter, opts...)
	if err != nil {
		return nil, err
	}
	defer cur.Close(ctx)
	var out []bson.M
	if err := cur.All(ctx, &out); err != nil {
		return nil, err
	}
	return out, nil
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

	ctx, cancel := context.WithTimeout(context.Background(), 15*time.Second)
	defer cancel()

	client, err := mongo.Connect(ctx, options.Client().ApplyURI(uri))
	if err != nil {
		log.Fatal(err)
	}
	defer func() { _ = client.Disconnect(context.Background()) }()

	coll := client.Database(dbName).Collection(collName)

	userFilter := map[string]interface{}{
		"status": "active",
		"score":  map[string]interface{}{"$gte": 10},
	}

	docs, err := QueryMongoDB(ctx, coll, userFilter, options.Find().SetLimit(50))
	if err != nil {
		log.Fatal(err)
	}
	for _, d := range docs {
		fmt.Println(d)
	}
}
