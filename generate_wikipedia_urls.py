#!/usr/bin/env python3
"""
Simple Wikipedia URL Generator
===============================
Generates Wikipedia URLs for missing breeds without testing
"""

def load_missing_breeds(filename='missing_breeds.txt'):
    """Load list of missing breeds from file"""
    with open(filename, 'r') as f:
        return [line.strip() for line in f if line.strip()]

def breed_to_wikipedia_url(breed_name):
    """Convert breed name to Wikipedia URL"""
    # Handle special characters and create URL
    wiki_name = breed_name.replace(' ', '_')
    
    # Handle special cases that need (dog) suffix
    needs_dog_suffix = [
        'Pointer', 'Brittany', 'Bulldog', 'Tosa', 'Shikoku',
        'Landseer', 'Pumi', 'Barbet', 'Beagle', 'Borzoi',
        'Boxer', 'Briard', 'Chinook', 'Dalmatian', 'Eurasier',
        'Havanese', 'Hovawart', 'Keeshond', 'Komondor', 'Kuvasz',
        'Leonberger', 'Maltese', 'Newfoundland', 'Papillon', 
        'Pekingese', 'Pomeranian', 'Poodle', 'Pug', 'Rottweiler',
        'Saluki', 'Samoyed', 'Schipperke', 'Vizsla', 'Weimaraner',
        'Whippet', 'Akita', 'Basenji', 'Collie', 'Greyhound'
    ]
    
    # Check if breed needs (dog) suffix
    for breed in needs_dog_suffix:
        if breed.lower() in breed_name.lower():
            wiki_name = wiki_name + '_(dog)'
            break
    
    return f"https://en.wikipedia.org/wiki/{wiki_name}"

def main():
    """Generate Wikipedia URLs for all missing breeds"""
    print("Loading missing breeds...")
    missing_breeds = load_missing_breeds()
    print(f"Found {len(missing_breeds)} missing breeds")
    
    # Generate URLs
    wikipedia_urls = []
    
    print("\nGenerating Wikipedia URLs...")
    for breed in missing_breeds:
        url = breed_to_wikipedia_url(breed)
        wikipedia_urls.append(f"{breed}|{url}")
    
    # Save results
    with open('wikipedia_urls.txt', 'w') as f:
        for entry in wikipedia_urls:
            f.write(f"{entry}\n")
    
    # Print summary
    print("\n" + "="*60)
    print("WIKIPEDIA URL GENERATION COMPLETE")
    print("="*60)
    print(f"Total breeds processed: {len(missing_breeds)}")
    print(f"URLs generated: {len(wikipedia_urls)}")
    print(f"\nResults saved to: wikipedia_urls.txt")
    
    # Show first 10 URLs as examples
    print("\nFirst 10 URLs generated:")
    for entry in wikipedia_urls[:10]:
        breed, url = entry.split('|')
        print(f"  {breed}: {url}")

if __name__ == "__main__":
    main()