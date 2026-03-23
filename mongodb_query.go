package main

import (
	"context"
	"fmt"
	"log"
	"time"

	"go.mongodb.org/mongo-driver/bson"
	"go.mongodb.org/mongo-driver/mongo"
	"go.mongodb.org/mongo-driver/mongo/options"
)

func QueryMongoDB(connectionString string, databaseName string, collectionName string, filterParams map[string]interface{}) ([]bson.M, error) {
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	client, err := mongo.Connect(ctx, options.Client().ApplyURI(connectionString))
	if err != nil {
		return nil, fmt.Errorf("failed to connect to MongoDB: %w", err)
	}
	defer func() {
		if err = client.Disconnect(ctx); err != nil {
			log.Printf("failed to disconnect from MongoDB: %v", err)
		}
	}()

	collection := client.Database(databaseName).Collection(collectionName)

	filter := bson.M{}
	for key, value := range filterParams {
		filter[key] = value
	}

	cursor, err := collection.Find(ctx, filter)
	if err != nil {
		return nil, fmt.Errorf("failed to execute query: %w", err)
	}
	defer cursor.Close(ctx)

	var results []bson.M
	if err = cursor.All(ctx, &results); err != nil {
		return nil, fmt.Errorf("failed to decode results: %w", err)
	}

	return results, nil
}

func main() {
	connectionString := "mongodb://localhost:27017"
	databaseName := "testdb"
	collectionName := "users"

	filterParams := map[string]interface{}{
		"status": "active",
		"age":    bson.M{"$gte": 18},
		"city":   "New York",
	}

	results, err := QueryMongoDB(connectionString, databaseName, collectionName, filterParams)
	if err != nil {
		log.Fatal(err)
	}

	for _, result := range results {
		fmt.Printf("%+v\n", result)
	}
}