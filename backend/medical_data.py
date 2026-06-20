MEDICAL_INFO = {
    'Cataract': {
        'name': 'Cataract',
        'group': 'Anterior Segment',
        'color': '#3B82F6',
        'analysis': "Visual examination reveals opacification of the crystalline lens, appearing as a grey, white, or yellowish clouding behind the pupil. The red reflex is likely diminished or absent. This indicates a disruption in the structural arrangement of lens fibers.",
        'description': "A cataract is a progressive clouding of the eye's natural lens, which lies behind the iris and the pupil. It is the leading cause of vision loss worldwide. Most cataracts develop slowly over the course of years due to aging, oxidative stress, or metabolic disorders like diabetes, preventing light from focusing sharply on the retina.",
        'symptoms': [
            "Cloudy, blurry, or dim vision similar to looking through a frosty window",
            "Increasing difficulty with vision at night",
            "Sensitivity to light and glare",
            "Seeing 'halos' around lights",
            "Frequent changes in eyeglass or contact lens prescription",
            "Fading or yellowing of colors",
            "Double vision in a single eye"
        ],
        'treatment': [
            "Prescription glasses or magnification aids (early stage)",
            "Phacoemulsification: The standard surgical procedure to emulsify the cloudy lens with ultrasound and remove it",
            "Intraocular Lens (IOL) Implantation: Replacing the natural lens with an artificial one"
        ],
        'precautions': [
            "Wear sunglasses that block 100% of UV rays to slow progression",
            "Quit smoking, as it accelerates lens oxidation",
            "Manage other health problems, especially diabetes",
            "Choose a healthy diet that includes plenty of fruits and vegetables (antioxidants)",
            "Reduce alcohol use"
        ],
        'severity': "Moderate to Severe (depending on opacity density)",
        'advice': "Surgery is the only effective cure and is highly successful. Consult an ophthalmologist to determine if the cataract is mature enough for removal or if it significantly interferes with daily activities like driving or reading."
    },
    'Conjunctivitis': {
        'name': 'Conjunctivitis',
        'group': 'Ocular Surface',
        'color': '#10B981',
        'analysis': "The bulbar conjunctiva (white part of the eye) exhibits significant hyperemia (redness) due to dilated blood vessels. There may be visible discharge (watery, mucoid, or purulent) and chemosis (swelling of the conjunctiva). The eyelids may appear slightly swollen.",
        'description': "Conjunctivitis, commonly known as 'Pink Eye', is the inflammation or infection of the transparent membrane (conjunctiva) that lines your eyelid and covers the white part of your eyeball. It can be caused by viruses (Adenovirus), bacteria, allergens (pollen, dust), or chemical irritants.",
        'symptoms': [
            "Pink or red color in the white of one or both eyes",
            "Itching, irritation, or burning sensation",
            "Excessive tearing (watery discharge - typical of viral/allergic)",
            "Thick yellow or green discharge that crusts over eyelashes (typical of bacterial)",
            "Gritty feeling, like sand in the eye",
            "Swelling of the eyelids"
        ],
        'treatment': [
            "Artificial tears to soothe irritation and dilute allergens",
            "Antibiotic eyedrops or ointment (only for bacterial cases)",
            "Antihistamine or mast cell stabilizer drops (for allergic conjunctivitis)",
            "Cold compresses to reduce swelling and itching",
            "Viral conjunctivitis usually resolves on its own within 7-14 days"
        ],
        'precautions': [
            "Do not touch or rub your eyes",
            "Wash hands frequently with soap and warm water",
            "Wash discharge from eyes several times a day using a fresh cotton ball",
            "Do not use the same eye drop dispenser for infected and non-infected eyes",
            "Change pillowcases and towels daily; do not share them",
            "Discard old eye makeup and do not wear contact lenses until healed"
        ],
        'severity': "Low (usually self-limiting, but contagious)",
        'advice': "If the discharge is thick/yellow or pain is moderate, see a doctor for antibiotics. Practice strict hygiene to prevent spreading it to others or your other eye. If vision is affected, seek immediate care."
    },
    'Eyelid': {
        'name': 'Eyelid Conditions',
        'group': 'Adnexal/Oculoplastic',
        'color': '#06B6D4',
        'analysis': "Localized swelling or inflammation is observed on the eyelid margin or body. There may be a distinct nodule (Chalazion/Stye) or generalized redness and crusting along the lash line (Blepharitis). The eyelid skin appears erythematous.",
        'description': "This classification covers general inflammatory conditions of the eyelid, including Hordeolum (Stye), Chalazion, and Blepharitis. These conditions involve the oil glands (Meibomian glands), eyelash follicles, or the eyelid skin itself, often leading to tenderness and blockage.",
        'symptoms': [
            "Red, painful lump near the edge of the eyelid (Stye)",
            "Painless but firm lump further back on the eyelid (Chalazion)",
            "Greasy flakes or crusting at the base of eyelashes (Blepharitis)",
            "Swollen, red, or itchy eyelids",
            "Sensitivity to light",
            "Feeling of a foreign object in the eye"
        ],
        'treatment': [
            "Warm Compresses: Applied for 10-15 minutes, 4 times a day (Crucial for drainage)",
            "Eyelid Scrubs: Gently cleaning the lash line with baby shampoo or dedicated lid wipes",
            "Antibiotic ointment or steroid eye drops for persistent infection/inflammation",
            "Oral antibiotics (Doxycycline) for chronic blepharitis",
            "Surgical drainage if a chalazion does not resolve after weeks"
        ],
        'precautions': [
            "Keep eyelids clean; practice daily lid hygiene",
            "Remove all eye makeup before sleeping",
            "Avoid using eyeliner or mascara while inflammation is present",
            "Do NOT squeeze, pop, or rub a stye or chalazion; this can spread infection"
        ],
        'severity': "Low (Painful but rarely dangerous)",
        'advice': "Consistency with warm compresses is key. Most styes/chalazia resolve on their own with heat therapy. If the swelling affects vision or the lid becomes very red and hot (preseptal cellulitis), seek medical attention immediately."
    },
    'Jaundice': {
        'name': 'Jaundice',
        'group': 'Ocular Surface',
        'color': '#F59E0B',
        'analysis': "Scleral Icterus is present: The sclera (normally white part of the eye) has a distinct yellow discoloration. This is a clinical manifestation of hyperbilirubinemia, where excess bilirubin deposits in the conjunctival tissues.",
        'description': "Jaundice of the eye is not a disease of the eye itself but a vital systemic warning sign. It indicates high levels of bilirubin in the blood, which suggests the liver, gallbladder, or pancreas is not functioning correctly. Causes include hepatitis, cirrhosis, gallstones, or hemolytic anemia.",
        'symptoms': [
            "Yellowing of the whites of the eyes",
            "Yellowing of the skin",
            "Dark or brown-colored urine",
            "Pale, clay-colored stools",
            "Fatigue, nausea, and abdominal pain"
        ],
        'treatment': [
            "The eye condition cannot be treated directly; the underlying systemic cause must be addressed",
            "Treatment ranges from antiviral medication (Hepatitis) to surgery (Gallstones) or lifestyle changes (Alcohol cessation)",
            "Hydration and rest"
        ],
        'precautions': [
            "Avoid alcohol completely to protect the liver",
            "Do not take medications (like Acetaminophen) without doctor approval",
            "Eat a liver-friendly diet (low fat, high fiber)",
            "Stay hydrated"
        ],
        'severity': "High (Systemic Medical Emergency)",
        'advice': "This is a critical indicator of internal organ dysfunction. You must see a General Practitioner, Internist, or Gastroenterologist immediately for blood tests (LFTs) and ultrasound. Do not ignore this."
    },
    'Uveitis': {
        'name': 'Uveitis',
        'group': 'Anterior Segment',
        'color': '#EF4444',
        'analysis': "Examination shows ciliary flush (redness around the iris) and potential miosis (constricted pupil). The eye appears deeply inflamed compared to surface redness. This involves inflammation of the uveal tract (Iris, Ciliary Body, Choroid).",
        'description': "Uveitis is the inflammation of the middle layer of the eye (uvea). It is a serious condition that can destroy eye tissue and lead to permanent vision loss. It is often associated with autoimmune disorders (like Rheumatoid Arthritis, Lupus) or infections (Herpes, Syphilis), though many cases are idiopathic.",
        'symptoms': [
            "Deep, boring eye pain (not just surface irritation)",
            "Severe redness (often a ring around the iris)",
            "Extreme sensitivity to light (Photophobia)",
            "Blurred or cloudy vision",
            "Seeing dark floating spots (floaters)",
            "Decreased vision"
        ],
        'treatment': [
            "Corticosteroid eye drops (prednisolone) to reduce inflammation aggressively",
            "Cycloplegic (dilating) drops to reduce pain and prevent iris scarring",
            "Oral steroids or immunosuppressive drugs for systemic/posterior cases",
            "Antiviral or antibiotic medication if an infection is the cause"
        ],
        'precautions': [
            "Wear dark glasses to manage light sensitivity",
            "Adhere strictly to the steroid drop schedule (do not stop abruptly)",
            "Screen for underlying autoimmune conditions",
            "Regular monitoring of eye pressure (steroids can raise IOP)"
        ],
        'severity': "High (Sight-Threatening Emergency)",
        'advice': "This is an ocular emergency. Untreated uveitis can lead to glaucoma, cataracts, and blindness. Seek a uveitis specialist or ophthalmologist immediately."
    },
    'Normal': {
        'name': 'Normal',
        'group': 'All Groups',
        'color': '#22C55E',
        'analysis': "The sclera is white and clear. The conjunctiva is pink and healthy with no discharge. The cornea is transparent with no opacities. Eyelids and lashes appear healthy with no signs of inflammation.",
        'description': "The eye appears structurally normal with no visible signs of external pathology. The anterior segment structures (cornea, iris, pupil) are intact and healthy in appearance.",
        'symptoms': [
            "No pain, redness, or discharge",
            "Clear vision",
            "No sensitivity to light"
        ],
        'treatment': [
            "No medical treatment required",
            "Routine maintenance"
        ],
        'precautions': [
            "Wear UV-protective sunglasses outdoors",
            "Follow the 20-20-20 rule: Every 20 mins, look 20 feet away for 20 seconds (digital eye strain)",
            "Wear protective eyewear during sports or hazardous work",
            "Maintain a diet rich in Omega-3 and Vitamin A",
            "Avoid smoking"
        ],
        'severity': "None",
        'advice': "Your eyes look healthy. Keep up routine eye exams every 1-2 years so a doctor can catch issues that are not visible in an external eye photo."
    },
    'Pterygium': {
        'name': 'Pterygium',
        'group': 'Ocular Surface',
        'color': '#8B5CF6',
        'analysis': "A wedge-shaped, fibrovascular growth is visible extending from the nasal conjunctiva onto the cornea. The tissue appears pink and fleshy. It may be encroaching on the visual axis.",
        'description': "A Pterygium (Surfer's Eye) is a raised, wedge-shaped growth of the conjunctiva that extends onto the cornea. It is benign but can cause irritation and astigmatism. It is strongly linked to long-term exposure to UV light, dust, and wind.",
        'symptoms': [
            "Pink, fleshy growth on the white of the eye (usually nasal side)",
            "Sensation of a foreign body in the eye",
            "Redness and inflammation",
            "Dryness and itching",
            "Blurred vision if the growth pulls on the cornea (astigmatism) or covers the pupil"
        ],
        'treatment': [
            "Lubricating artificial tears for comfort",
            "Steroid eye drops for short-term inflammation",
            "Surgical excision: Removal of the growth, often with a conjunctival autograft to prevent recurrence",
            "Prescription eyewear to correct induced astigmatism"
        ],
        'precautions': [
            "Strict UV protection: Wear wrap-around sunglasses and wide-brimmed hats outdoors",
            "Protect eyes from dust and wind",
            "Use lubricating drops in dry environments"
        ],
        'severity': "Moderate (Can threaten vision if it grows large)",
        'advice': "Monitor the growth size. If it starts to reach the pupil or causes persistent irritation despite drops, surgical removal is recommended. UV protection is critical to stop it from growing."
    }
}
