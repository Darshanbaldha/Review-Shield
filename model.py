# -*- coding: utf-8 -*-
import pandas as pd
import random
import re
import string

def preprocess_text(text):
    """Clean and preprocess review text"""
    if not text or pd.isna(text):
        return ""
    
    text = str(text).lower()
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    # Remove special characters but keep basic punctuation
    text = re.sub(r'[^\w\s.,!?-]', '', text)
    return text

def calculate_fake_score(review_text):
    """Calculate likelihood of review being fake based on patterns - ULTRA AGGRESSIVE MODE"""
    text = preprocess_text(review_text)
    fake_score = 0
    
    # MASSIVELY EXPANDED fake review patterns (Indian e-commerce specific)
    fake_patterns = [
        # Superlatives
        r'\b(amazing|awesome|perfect|excellent|outstanding|phenomenal|incredible|superb|fantastic|wonderful|brilliant|fabulous|marvelous|spectacular|stunning|breathtaking)\b',
        # Best/Top patterns
        r'\b(best|greatest|finest|top|ultimate|supreme|premier) (product|item|purchase|buy|thing|deal|choice)\b',
        # Recommendation patterns
        r'\bhighly recommend\b',
        r'\bstrongly recommend\b',
        r'\bwould recommend\b',
        r'\brecommend (it|this)\b',
        # Must buy patterns
        r'\bmust buy\b',
        r'\bmust have\b',
        r'\bmust purchase\b',
        r'\bshould buy\b',
        # Star patterns
        r'\b5 stars?\b',
        r'\bfive stars?\b',
        r'\b5/5\b',
        r'\b10/10\b',
        # Delivery patterns (often fake)
        r'\bsuper fast delivery\b',
        r'\bfast delivery\b',
        r'\bquick delivery\b',
        r'\bon time delivery\b',
        r'\btimely delivery\b',
        # Expectation patterns
        r'\bexceeded expectations\b',
        r'\bbeyond expectations\b',
        r'\bmet expectations\b',
        # Value patterns
        r'\bmoney well spent\b',
        r'\bworth every penny\b',
        r'\bworth every rupee\b',
        r'\bbest purchase ever\b',
        r'\bvalue for money\b',
        r'\bpaisa vasool\b',
        r'\bvfm\b',
        # Satisfaction patterns
        r'\btotally satisfied\b',
        r'\bfully satisfied\b',
        r'\bcompletely satisfied\b',
        r'\b100%\s*(satisfied|genuine|authentic|original|recommended|happy)\b',
        # Quality patterns
        r'\bgreat quality\b',
        r'\bgood quality\b',
        r'\bexcellent quality\b',
        r'\bsuperior quality\b',
        r'\btop quality\b',
        r'\bbest quality\b',
        # Product praise patterns
        r'\bnice product\b',
        r'\bgood product\b',
        r'\bgreat product\b',
        r'\blove it\b',
        r'\bloved it\b',
        r'\bloving it\b',
        r'\bamazing product\b',
        r'\bawesome product\b',
        r'\bexcellent product\b',
        r'\bsuperb product\b',
        # Generic praise
        r'\bvery (good|nice|happy|satisfied)\b',
        r'\bso (good|nice|happy|satisfied|glad)\b',
        r'\breally (good|nice|great|happy)\b',
    ]
    
    # MASSIVELY EXPANDED suspicious characteristics
    suspicious_patterns = [
        # Urgency patterns
        r'\b(buy|purchase|get|order) (this|it) (now|today|immediately|right now|asap)\b',
        r'\bdon\'t (hesitate|wait|think twice|delay)\b',
        r'\bworthwhile investment\b',
        r'\bgo for it\b',
        r'\bjust (buy|get|order|go for) it\b',
        r'\bno regrets\b',
        r'\bno doubt\b',
        r'\bwithout (any )?doubt\b',
        # Deal patterns
        r'\bbest deal\b',
        r'\bgreat deal\b',
        r'\bgood deal\b',
        r'\bamazing deal\b',
        r'\btotally worth it\b',
        r'\bcompletely worth it\b',
        r'\bdefinitely worth\b',
        # Indian specific
        r'\bpaisa vasool\b',
        r'\bbargain price\b',
        r'\bvalue pack\b',
        # Purchase encouragement
        r'\bgood buy\b',
        r'\bnice buy\b',
        r'\bgreat buy\b',
        r'\bbest buy\b',
        r'\bworth buying\b',
        r'\bwill buy again\b',
        r'\bwould buy again\b',
        r'\bgo ahead\b',
        r'\bgo for this\b',
        r'\bblindly buy\b',
        r'\bblindly go for\b',
        r'\bdon\'t think (twice|much)\b',
        r'\b(you|u) (should|must|can) buy\b',
        # Comparison patterns (often fake)
        r'\bbetter than\b',
        r'\bbest in\b',
        r'\btop in\b',
        # As described (generic)
        r'\bas (shown|described|expected)\b',
        r'\bsame as (pic|picture|image)\b',
    ]
    
    # Check for fake patterns - COUNT ALL OCCURRENCES
    for pattern in fake_patterns:
        matches = re.findall(pattern, text)
        if matches:
            fake_score += 0.8 * len(matches)  # Each occurrence adds points
    
    for pattern in suspicious_patterns:
        matches = re.findall(pattern, text)
        if matches:
            fake_score += 0.7 * len(matches)
    
    # Length-based scoring - VERY AGGRESSIVE
    word_count = len(text.split())
    if word_count < 5:  # Very short reviews
        fake_score += 3.0
    elif word_count < 8:  # Short reviews
        fake_score += 2.0
    elif word_count < 12:  # Still quite short
        fake_score += 1.0
    elif word_count < 18:  # Somewhat short
        fake_score += 0.5
    elif word_count > 300:  # Very long reviews (also suspicious)
        fake_score += 1.0
    
    # MASSIVELY EXPANDED generic phrases
    generic_phrases = [
        'good product', 'nice product', 'quality product', 
        'good quality', 'nice quality', 'recommend this',
        'great product', 'awesome product', 'excellent product',
        'good one', 'nice one', 'superb product', 'loved it',
        'worth buying', 'good buy', 'satisfied', 'happy with purchase',
        'as expected', 'as described', 'value for money',
        'must buy', 'best product', 'nice purchase',
        'satisfied with', 'happy with', 'good purchase',
        'nice choice', 'good choice', 'perfect product',
        'awesome quality', 'super product', 'great buy',
        'nice buy', 'good deal', 'great deal', 'best buy',
        'worth it', 'totally worth', 'paisa vasool',
        'loved this', 'love this', 'like it', 'liked it',
        'satisfied customer', 'happy customer', 'repeat customer',
        'will recommend', 'highly recommended', 'strongly recommended',
        'go for it', 'just buy', 'must have',
        'fast delivery', 'good delivery', 'quick delivery',
        'nice packaging', 'good packaging', 'proper packaging',
        'original product', 'genuine product', 'authentic product',
        'value pack', 'good value', 'great value',
    ]
    
    phrase_count = 0
    for phrase in generic_phrases:
        if phrase in text:
            phrase_count += 1
            fake_score += 0.6
    
    # Multiple generic phrases = super suspicious
    if phrase_count >= 3:
        fake_score += 1.5
    elif phrase_count >= 2:
        fake_score += 0.8
    
    # Excessive punctuation - VERY AGGRESSIVE
    exclamation_count = text.count('!')
    if exclamation_count > 5:
        fake_score += 3.5
    elif exclamation_count > 3:
        fake_score += 2.5
    elif exclamation_count > 2:
        fake_score += 1.5
    elif exclamation_count > 0:
        fake_score += 0.5
    
    question_count = text.count('?')
    if question_count > 2:
        fake_score += 1.5
    elif question_count > 0:
        fake_score += 0.5
    
    # All caps words - VERY AGGRESSIVE
    words = text.split()
    caps_words = [word for word in words if word.isupper() and len(word) > 2]
    if len(caps_words) > 4:
        fake_score += 2.5
    elif len(caps_words) > 2:
        fake_score += 1.8
    elif len(caps_words) > 1:
        fake_score += 1.0
    elif len(caps_words) > 0:
        fake_score += 0.5
    
    # Repetitive words - ENHANCED
    word_freq = {}
    for word in words:
        if len(word) > 3:
            word_lower = word.lower()
            word_freq[word_lower] = word_freq.get(word_lower, 0) + 1
    
    max_repetition = max(word_freq.values()) if word_freq else 0
    if max_repetition > 5:
        fake_score += 2.5
    elif max_repetition > 3:
        fake_score += 1.5
    elif max_repetition > 2:
        fake_score += 0.8
    
    # Too positive without specifics - VERY AGGRESSIVE
    positive_words = ['good', 'great', 'excellent', 'amazing', 'awesome', 
                     'perfect', 'nice', 'best', 'super', 'fantastic', 
                     'wonderful', 'love', 'loved', 'brilliant', 'superb',
                     'outstanding', 'fabulous', 'happy', 'satisfied', 'glad']
    positive_count = sum(1 for word in positive_words if word in text)
    
    # Aggressive scoring for positive word density
    if positive_count >= 5 and word_count < 60:
        fake_score# -*- coding: utf-8 -*-
import pandas as pd
import random
import re
import string

def preprocess_text(text):
    """Clean and preprocess review text"""
    if not text or pd.isna(text):
        return ""
    
    text = str(text).lower()
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    # Remove special characters but keep basic punctuation
    text = re.sub(r'[^\w\s.,!?-]', '', text)
    return text

def calculate_fake_score(review_text):
    """Calculate likelihood of review being fake based on patterns - AGGRESSIVE MODE"""
    text = preprocess_text(review_text)
    fake_score = 0
    
    # Common fake review patterns - HIGHLY EXPANDED
    fake_patterns = [
        r'\b(amazing|awesome|perfect|excellent|outstanding|phenomenal|incredible|superb|fantastic|wonderful|brilliant|fabulous|marvelous)\b',
        r'\b(best|greatest|finest|top|ultimate) (product|item|purchase|buy|thing|deal)\b',
        r'\bhighly recommend\b',
        r'\bmust buy\b',
        r'\b5 stars?\b',
        r'\bfive stars?\b',
        r'\bsuper fast delivery\b',
        r'\bexceeded expectations\b',
        r'\bmoney well spent\b',
        r'\bworth every penny\b',
        r'\bbest purchase ever\b',
        r'\bvalue for money\b',
        r'\btotally satisfied\b',
        r'\b100%\s*(satisfied|genuine|authentic|original|recommended)\b',
        r'\bgreat quality\b',
        r'\bgood quality\b',
        r'\bnice product\b',
        r'\blove it\b',
        r'\bloved it\b',
        r'\bamazing product\b',
        r'\bawesome product\b',
        r'\bexcellent product\b',
    ]
    
    # Suspicious characteristics - HIGHLY EXPANDED
    suspicious_patterns = [
        r'\b(buy|purchase|get|order) (this|it) (now|today|immediately|right now)\b',
        r'\bdon\'t (hesitate|wait|think twice)\b',
        r'\bworthwhile investment\b',
        r'\bgo for it\b',
        r'\bjust (buy|get|order) it\b',
        r'\bno regrets\b',
        r'\bbest deal\b',
        r'\btotally worth it\b',
        r'\bpaisa vasool\b',
        r'\bbargain price\b',
        r'\bgood buy\b',
        r'\bnice buy\b',
        r'\bworth buying\b',
        r'\bwill buy again\b',
        r'\bgo ahead\b',
        r'\bblindly buy\b',
        r'\bdon\'t think (twice|much)\b',
    ]
    
    # Check for fake patterns - INCREASED scoring
    for pattern in fake_patterns:
        matches = re.findall(pattern, text)
        if matches:
            fake_score += 1.0 * len(matches)  # Count multiple occurrences
    
    for pattern in suspicious_patterns:
        matches = re.findall(pattern, text)
        if matches:
            fake_score += 0.8 * len(matches)
    
    # Length-based scoring - MORE AGGRESSIVE
    word_count = len(text.split())
    if word_count < 5:  # Very short reviews
        fake_score += 2.5
    elif word_count < 10:  # Short reviews
        fake_score += 1.5
    elif word_count < 15:  # Still quite short
        fake_score += 0.5
    elif word_count > 300:  # Very long reviews (also suspicious)
        fake_score += 1.0
    
    # Generic phrases (often in fake reviews) - MASSIVELY EXPANDED
    generic_phrases = [
        'good product', 'nice product', 'quality product', 
        'good quality', 'nice quality', 'recommend this',
        'great product', 'awesome product', 'excellent product',
        'good one', 'nice one', 'superb product', 'loved it',
        'worth buying', 'good buy', 'satisfied', 'happy with purchase',
        'as expected', 'as described', 'value for money',
        'must buy', 'best product', 'nice purchase',
        'satisfied with', 'happy with', 'good purchase',
        'nice choice', 'good choice', 'perfect product',
        'awesome quality', 'super product', 'great buy',
        'nice buy', 'good deal', 'great deal', 'best buy',
        'worth it', 'totally worth', 'paisa vasool',
    ]
    
    for phrase in generic_phrases:
        if phrase in text:
            fake_score += 0.7
    
    # Excessive punctuation - MORE AGGRESSIVE
    exclamation_count = text.count('!')
    if exclamation_count > 5:
        fake_score += 3.0
    elif exclamation_count > 3:
        fake_score += 2.0
    elif exclamation_count > 1:
        fake_score += 1.0
    
    question_count = text.count('?')
    if question_count > 2:
        fake_score += 1.0
    
    # All caps words (excitement indicators) - MORE AGGRESSIVE
    words = text.split()
    caps_words = [word for word in words if word.isupper() and len(word) > 2]
    if len(caps_words) > 4:
        fake_score += 2.0
    elif len(caps_words) > 2:
        fake_score += 1.5
    elif len(caps_words) > 0:
        fake_score += 0.5
    
    # Repetitive words - ENHANCED
    word_freq = {}
    for word in words:
        if len(word) > 3:
            word_lower = word.lower()
            word_freq[word_lower] = word_freq.get(word_lower, 0) + 1
    
    max_repetition = max(word_freq.values()) if word_freq else 0
    if max_repetition > 4:
        fake_score += 2.0
    elif max_repetition > 2:
        fake_score += 1.0
    
    # Too positive without specifics - ENHANCED
    positive_words = ['good', 'great', 'excellent', 'amazing', 'awesome', 
                     'perfect', 'nice', 'best', 'super', 'fantastic', 
                     'wonderful', 'love', 'loved', 'brilliant']
    positive_count = sum(1 for word in positive_words if word in text)
    
    # If many positive words but short review = likely fake
    if positive_count >= 4 and word_count < 50:
        fake_score += 2.5
    elif positive_count >= 3 and word_count < 30:
        fake_score += 2.0
    elif positive_count >= 2 and word_count < 20:
        fake_score += 1.5
    
    # No specific details - ENHANCED
    specific_indicators = [
        'because', 'but', 'however', 'although', 'after', 'before',
        'when', 'while', 'using', 'used', 'feature', 'features',
        'quality', 'material', 'size', 'color', 'price', 'delivery',
        'packaging', 'condition', 'performance', 'day', 'week', 'month',
        'issue', 'problem', 'like', 'dislike', 'compared', 'better',
        'worse', 'pros', 'cons', 'advantage', 'disadvantage'
    ]
    has_specifics = sum(1 for indicator in specific_indicators if indicator in text)
    
    if has_specifics == 0 and word_count > 10:
        fake_score += 2.0
    elif has_specifics <= 1 and word_count > 15:
        fake_score += 1.0
    
    # Suspicious emoji/emoticon patterns (if present)
    emoji_pattern = r'[😀😁😂🤣😃😄😅😆😉😊😋😎😍😘🥰😗😙😚]'
    emoji_count = len(re.findall(emoji_pattern, review_text))
    if emoji_count > 3:
        fake_score += 1.5
    elif emoji_count > 1:
        fake_score += 0.5
    
    # Ratio of positive words to total words
    positive_ratio = positive_count / word_count if word_count > 0 else 0
    if positive_ratio > 0.3:  # More than 30% positive words
        fake_score += 1.5
    elif positive_ratio > 0.2:  # More than 20% positive words
        fake_score += 1.0
    
    # Single sentence reviews (often fake)
    sentence_count = text.count('.') + text.count('!') + text.count('?')
    if sentence_count <= 1 and word_count > 5:
        fake_score += 1.0
    
    # Common fake review starter phrases
    starter_phrases = [
        text.startswith(phrase) for phrase in [
            'nice', 'good', 'great', 'excellent', 'amazing',
            'awesome', 'best', 'super', 'must buy', 'highly recommend'
        ]
    ]
    if any(starter_phrases):
        fake_score += 1.0
    
    # Repetitive patterns (e.g., "good good good")
    if re.search(r'\b(\w+)\s+\1\s+\1\b', text):
        fake_score += 2.0
    elif re.search(r'\b(\w+)\s+\1\b', text):
        fake_score += 1.0
    
    return fake_score

def detect_fake_review(review_text):
    """
    Determine if a review is fake or original - VERY AGGRESSIVE MODE
    Replace this logic with your trained ML model
    """
    fake_score = calculate_fake_score(review_text)
    
    # MUCH LOWER threshold for aggressive detection
    # Old: >= 3.0, New: >= 2.0
    if fake_score >= 2.0:
        return "Fake"
    else:
        return "Original"

def check_reviews(reviews):
    """
    Process list of reviews and return DataFrame with predictions
    
    Args:
        reviews (list): List of review texts
    
    Returns:
        pd.DataFrame: DataFrame with 'review' and 'prediction' columns
    """
    if not reviews:
        return pd.DataFrame(columns=['review', 'prediction'])
    
    data = []
    processed_count = 0
    fake_count = 0
    original_count = 0
    
    # Score distribution tracking
    score_distribution = []
    
    for review in reviews:
        if review and len(str(review).strip()) > 0:
            review_text = str(review).strip()
            
            # Skip very short reviews
            if len(review_text) < 10:
                continue
                
            # Calculate score for debugging
            score = calculate_fake_score(review_text)
            score_distribution.append(score)
            
            # Detect fake vs original
            prediction = detect_fake_review(review_text)
            
            # Count predictions
            if prediction == "Fake":
                fake_count += 1
            else:
                original_count += 1
            
            data.append({
                "review": review_text,
                "prediction": prediction
            })
            
            processed_count += 1
    
    # Calculate statistics
    if score_distribution:
        avg_score = sum(score_distribution) / len(score_distribution)
        max_score = max(score_distribution)
        min_score = min(score_distribution)
        
        print(f"\n{'='*60}")
        print(f"FAKE DETECTION STATISTICS")
        print(f"{'='*60}")
        print(f"Total Reviews Processed: {processed_count}")
        print(f"Fake Reviews Found: {fake_count} ({(fake_count/processed_count*100):.1f}%)")
        print(f"Original Reviews Found: {original_count} ({(original_count/processed_count*100):.1f}%)")
        print(f"\nScore Statistics:")
        print(f"  Average Score: {avg_score:.2f}")
        print(f"  Highest Score: {max_score:.2f}")
        print(f"  Lowest Score: {min_score:.2f}")
        print(f"  Detection Threshold: 2.0 (scores >= 2.0 = Fake)")
        print(f"{'='*60}\n")
        
        # Show sample classifications
        print("Sample Classifications:")
        for i, (review, score, pred) in enumerate(zip(reviews[:5], score_distribution[:5], 
                                                        [d['prediction'] for d in data[:5]])):
            print(f"\n{i+1}. Score: {score:.2f} → {pred}")
            print(f"   Review: {str(review)[:80]}...")
        print(f"{'='*60}\n")
    
    return pd.DataFrame(data)

# Optional: Advanced ML model placeholder
def load_ml_model():
    """
    Placeholder for loading a trained ML model
    Replace this with your actual model loading code
    """
    # Example:
    # import joblib
    # model = joblib.load('fake_review_model.pkl')
    # vectorizer = joblib.load('vectorizer.pkl')
    # return model, vectorizer
    pass

def predict_with_ml_model(reviews, model=None, vectorizer=None):
    """
    Placeholder for ML model prediction
    Replace this with your actual ML prediction code
    """
    # Example:
    # if model and vectorizer:
    #     features = vectorizer.transform(reviews)
    #     predictions = model.predict(features)
    #     return predictions
    # else:
    #     return [detect_fake_review(review) for review in reviews]
    
    return [detect_fake_review(review) for review in reviews]