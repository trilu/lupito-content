#!/usr/bin/env python3
"""
Script to update brand websites in food_brands_sc table
"""
import os
from datetime import datetime
from supabase import create_client, Client

# Initialize Supabase client
supabase_url = os.environ.get('SUPABASE_URL', 'https://cibjeqgftuxuezarjsdl.supabase.co')
supabase_key = os.environ.get('SUPABASE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNpYmplcWdmdHV4dWV6YXJqc2RsIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1Mzg1NTY2NywiZXhwIjoyMDY5NDMxNjY3fQ.ngzgvYr2zXisvkz03F86zNWPRHP0tEMX0gQPBm2z_jk')

supabase: Client = create_client(supabase_url, supabase_key)

# Brand websites found through web search
BRAND_WEBSITES = {
    # Top Raw Food Brands
    'Bella + Duke': 'https://www.bellaandduke.com',
    'ProDog Raw': 'https://www.prodograw.com',
    'Natural Instinct': 'https://www.naturalinstinct.com',
    'Nutriment': 'https://www.nutriment.co',
    'Cotswold Raw': 'https://www.cotswoldraw.com',
    'Paleo Ridge': 'https://www.paleoridge.co.uk',
    "Poppy's Picnic": 'https://www.poppyspicnic.co.uk',
    'Benyfit Natural': 'https://www.benyfitnatural.com',
    'Wolf Tucker': 'https://www.wolftucker.co.uk',
    'Raw & Simple': 'https://www.rawandsimple.co.uk',
    
    # Major Commercial Brands
    'Royal Canin': 'https://www.royalcanin.com/uk',
    'Hills Science Plan': 'https://www.hillspet.co.uk',
    "Hill's Science Plan": 'https://www.hillspet.co.uk',
    "Hill's Prescription Diet": 'https://www.hillspet.co.uk',
    'Pedigree': 'https://www.pedigreepetfoods.co.uk',
    'Purina': 'https://www.purina.co.uk',
    'Pro Plan': 'https://www.purina.co.uk/pro-plan',
    'Iams': 'https://www.iams.co.uk',
    'Eukanuba': 'https://www.eukanuba.co.uk',
    'Advance': 'https://www.advance-pet.co.uk',
    
    # Premium/Natural Brands
    'Orijen': 'https://www.orijenpetfoods.co.uk',
    'Acana': 'https://www.acanapetfoods.co.uk',
    'Canagan': 'https://www.canagan.co.uk',
    "Lily's Kitchen": 'https://www.lilyskitchen.co.uk',
    'Barking Heads': 'https://www.barkingheads.co.uk',
    'Eden': 'https://www.edenpetfoods.com',
    'Applaws': 'https://www.applaws.co.uk',
    'Natures Menu': 'https://www.naturesmenu.co.uk',
    "Nature's Menu": 'https://www.naturesmenu.co.uk',
    'Forthglade': 'https://www.forthglade.com',
    'Burns': 'https://www.burnspet.co.uk',
    'James Wellbeloved': 'https://www.wellbeloved.com',
    'Arden Grange': 'https://www.ardengrange.com',
    'Symply': 'https://www.symplypetfoods.com',
    'Harringtons': 'https://www.harringtonspetfood.com',
    'Pooch & Mutt': 'https://www.poochandmutt.com',
    'Scrumbles': 'https://www.scrumbles.co.uk',
    'Edgard & Cooper': 'https://www.edgardcooper.com/en-gb',
    'Guru': 'https://www.gurupetfood.com',
    'Piccolo': 'https://www.piccolo.pet',
    'Aatu': 'https://www.aatu.co.uk',
    'Akela': 'https://www.akeladog.co.uk',
    'Millies Wolfheart': 'https://www.millieswolfheart.co.uk',
    'Wolf of Wilderness': 'https://www.zooplus.co.uk/shop/dogs/dry_dog_food/wolf_of_wilderness',
    'Taste of the Wild': 'https://www.tasteofthewildpetfood.co.uk',
    'Carnilove': 'https://www.carnilove.co.uk',
    'Essential': 'https://www.essentialfoods.com',
    'Tribal': 'https://www.tribalpetfoods.co.uk',
    'Fish4Dogs': 'https://www.fish4dogs.com',
    
    # UK Supermarket Brands
    'Wagg': 'https://www.waggfoods.com',
    "Wainwright's": 'https://www.petsathome.com/shop/en/pets/wainwrights',
    'Bakers': 'https://www.purina.co.uk/bakers',
    'Butchers': 'https://www.butchersdogfood.co.uk',
    "Butcher's": 'https://www.butchersdogfood.co.uk',
    'Chappie': 'https://www.mars.com/made-by-mars/petcare',
    'Cesar': 'https://www.cesar.com',
    'Pedigree': 'https://www.pedigreepetfoods.co.uk',
    'Whiskas': 'https://www.whiskas.co.uk',
    
    # Vet Brands
    'Specific': 'https://www.specificdiet.co.uk',
    'Virbac': 'https://uk.virbac.com',
    'VetSpec': 'https://www.vetspec.co.uk',
    
    # Specialist/Other
    "Skinner's": 'https://www.skinnerspetfoods.co.uk',
    'CSJ': 'https://www.csjk9.com',
    'Burgess': 'https://www.burgesspetcare.com',
    'Arkwrights': 'https://www.arkwrights.net',
    'Simpsons': 'https://www.simpsons-premium.com',
    'Beta': 'https://www.beta-pet.co.uk',
    'Wellness': 'https://www.wellnesspetfood.co.uk',
    'Yarrah': 'https://www.yarrah.com/en-gb',
    'Ziwi Peak': 'https://www.ziwipets.com',
    'Rocco': 'https://www.zooplus.co.uk/shop/dogs/wet_dog_food/rocco',
    'Terra Canis': 'https://www.terracanis.de/en',
    'Lukullus': 'https://www.zooplus.co.uk/shop/dogs/wet_dog_food/lukullus',
    'Markus Muehle': 'https://www.markus-muehle.com',
    'Josera': 'https://www.josera.co.uk',
    'Happy Dog': 'https://www.happydog.co.uk',
    'Animonda': 'https://www.animonda.co.uk',
    'Belcando': 'https://www.belcando.co.uk',
    'Briantos': 'https://www.zooplus.co.uk/shop/dogs/dry_dog_food/briantos',
    'Greenwoods': 'https://www.zooplus.co.uk/shop/dogs/wet_dog_food/greenwoods',
    
    # Raw Food Specialists
    'Durham Animal Feeds': 'https://www.durhamanimalfeeds.co.uk',
    'Naturaw': 'https://www.naturaw.com',
    'RaaW': 'https://www.raawpetfood.com',
    'Embark on Raw': 'https://www.embarkonraw.com',
    'Wild Pet Food': 'https://www.thewildpetfood.com',
    'Drool': 'https://www.droolpetfood.com',
    
    # Smaller/Independent Brands
    "Green & Wilds": 'https://www.greenandwilds.com',
    'Different Dog': 'https://www.differentdog.com',
    'Pure Pet Food': 'https://www.purepetfood.com',
    'Tails.com': 'https://www.tails.com',
    'McAdams': 'https://www.mcadamspetfoods.com',
    'Laughing Dog': 'https://www.laughingdogfood.com',
    'Gentle': 'https://www.gentle-dog.co.uk',
    'Vitalin': 'https://www.vitalin.co.uk',
    'Trophy Pet Foods': 'https://www.trophypetfoods.co.uk',
    'Fold Hill': 'https://www.foldhill.co.uk',
    'Chudleys': 'https://www.chudleys.co.uk',
    'Skinners': 'https://www.skinnerspetfoods.co.uk',
    
    # Insect/Alternative Protein
    'Yora': 'https://www.yorapetfoods.com',
    'Grub Club': 'https://www.grubclub.co.uk',
    'Bug Bakes': 'https://www.bugbakes.co.uk',
    
    # Treats & Supplements
    'Whimzees': 'https://www.whimzees.com',
    'Yakers': 'https://www.yakers.co.uk',
    'Soopa Pets': 'https://www.soopapets.com',
    'Pet Munchies': 'https://www.petmunchies.com',
    
    # Store Brands
    'Pets at Home': 'https://www.petsathome.com',
    'Sainsburys': 'https://www.sainsburys.co.uk',
    "Sainsbury's": 'https://www.sainsburys.co.uk',
    'Tesco': 'https://www.tesco.com',
    'Asda': 'https://www.asda.com',
    'Morrisons': 'https://www.morrisons.com',
    'Waitrose': 'https://www.waitrose.com',
    'Wilko': 'https://www.wilko.com',
    'Amazon': 'https://www.amazon.co.uk',
}

def update_brand_website(brand_name: str, website_url: str):
    """Update a brand's website in the database"""
    try:
        response = supabase.table('food_brands_sc').update({
            'official_website': website_url,
            'official_website_verified': False,
            'website_discovery_method': 'web_search',
            'website_last_checked': datetime.utcnow().isoformat(),
            'scraping_status': 'ready',
            'updated_at': datetime.utcnow().isoformat()
        }).eq('brand_name', brand_name).execute()
        
        if response.data:
            return True
        return False
    except Exception as e:
        print(f"Error updating {brand_name}: {e}")
        return False

def main():
    print("="*80)
    print("UPDATING BRAND WEBSITES")
    print("="*80)
    
    successful = 0
    failed = 0
    
    for brand_name, website in sorted(BRAND_WEBSITES.items()):
        if update_brand_website(brand_name, website):
            print(f"✓ {brand_name}: {website}")
            successful += 1
        else:
            print(f"✗ {brand_name}: Failed to update")
            failed += 1
    
    print("\n" + "="*80)
    print(f"SUMMARY: Updated {successful} brands, {failed} failed")
    print("="*80)
    
    # Show statistics
    try:
        total = supabase.table('food_brands_sc').select('id', count='exact').execute()
        with_websites = supabase.table('food_brands_sc').select('id', count='exact').not_.is_('official_website', 'null').execute()
        ready = supabase.table('food_brands_sc').select('id', count='exact').eq('scraping_status', 'ready').execute()
        
        print(f"\nTotal brands: {total.count}")
        print(f"Brands with websites: {with_websites.count}")
        print(f"Brands ready for scraping: {ready.count}")
        print(f"Coverage: {(with_websites.count / total.count * 100):.1f}%")
    except Exception as e:
        print(f"Error getting statistics: {e}")

if __name__ == "__main__":
    main()