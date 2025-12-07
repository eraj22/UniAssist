import chromadb

# Connect to your ChromaDB
client = chromadb.PersistentClient(path="./data/chroma_db")

# List all collections
collections = client.list_collections()

print("📊 Found Collections:")
print("="*60)

if collections:
    for col in collections:
        print(f"\n✅ Collection Name: {col.name}")
        print(f"   ID: {col.id}")
        print(f"   Count: {col.count()} documents")
        print(f"   Metadata: {col.metadata}")
        
        # Get a sample document
        try:
            sample = col.peek(limit=1)
            if sample and sample['documents']:
                print(f"   Sample text: {sample['documents'][0][:100]}...")
        except:
            pass
else:
    print("❌ No collections found!")

print("\n" + "="*60)
print("\n💡 Use the collection name shown above in your agents!")