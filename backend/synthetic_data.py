import random

def generate_synthetic_rag_dataset() -> list[str]:
    """
    Generates a realistic raw dataset containing valid RAG documents (customer feedback, 
    support questions, technical queries) as well as garbage/noise (system logs, tracebacks, 
    gibberish, SQL injections, and off-topic comments).
    """
    
    valid_intents = [
        # Topic 1: Account & Password Issues
        "How do I reset my password if I lost my email access?",
        "My password reset link has expired, can I get a new one?",
        "Is there a way to enable multi-factor authentication (MFA) on my account?",
        "How can I change the primary email address associated with my profile?",
        "I'm locked out of my account due to too many failed login attempts. Help!",
        "Where can I find my account settings and security preferences?",
        "Can I merge two separate user accounts under the same billing name?",
        
        # Topic 2: Billing & Refund Requests
        "I was charged twice for this month's subscription. Can I get a refund?",
        "Where can I download the PDF invoices for my monthly billing statements?",
        "How do I update my credit card information for the next auto-renewal?",
        "Can I switch from a monthly billing cycle to an annual subscription?",
        "I want to request a full refund for my purchase as the product didn't fit my needs.",
        "Does the enterprise plan support invoice-based billing with net-30 terms?",
        "My coupon code was not applied at checkout, can I get a credit?",
        
        # Topic 3: System Performance & Latency
        "The web application UI is loading extremely slowly today. Is there an outage?",
        "I am getting a timeout error whenever I try to run a large search query.",
        "The page takes over 10 seconds to respond when uploading a 5MB PDF.",
        "Is there a status page where I can check if the API is experiencing latency?",
        "The customer dashboard is showing a loading spinner indefinitely.",
        "Our team is seeing intermittent performance drops on the European server node.",
        "Why does the database query sync take so long to complete on mobile?",

        # Topic 4: Python & SDK Configuration
        "How do I install and configure the Python SDK for your API?",
        "I'm getting a ModuleNotFoundError when trying to import the client library.",
        "Is there a code example showing how to initialize the client with custom headers?",
        "Does the SDK support asynchronous calls with python asyncio?",
        "How do I pass the API key securely using environment variables in Python?",
        "Where can I find the API reference documentation for the SDK endpoints?",
        "Is the client library compatible with Python 3.12 and above?"
    ]
    
    malicious_inputs = [
        # SQL Injection attempts
        "SELECT * FROM users WHERE username = 'admin' AND password = '1' OR '1'='1';",
        "UNION SELECT username, password, email FROM admin_users --",
        "'; DROP TABLE logs; --",
        "1' OR 1=1 --",
        "admin' AND 1=2 UNION SELECT NULL, version(), database()--",
        
        # XSS attempts
        "<script>alert('XSS vulnerability test')</script>",
        "<img src=x onerror=alert(document.cookie)>",
        "javascript:alert('system compromised')",
        "<iframe src='http://evil.com'></iframe>"
    ]
    
    system_noise = [
        # System tracebacks
        "Traceback (most recent call last):\n  File \"app/main.py\", line 42, in index\n    data = db.query(Query).all()\nAttributeError: 'NoneType' object has no attribute 'query'",
        "java.lang.NullPointerException\n\tat com.app.service.UserService.getUserDetails(UserService.java:87)\n\tat com.app.controller.UserController.getProfile(UserController.java:23)",
        "Exception in thread \"main\" java.lang.ArrayIndexOutOfBoundsException: Index 5 out of bounds for length 5",
        
        # Logs
        "127.0.0.1 - - [20/Jun/2026:01:23:45 +0000] \"GET /api/v1/status HTTP/1.1\" 200 452 \"-\" \"curl/7.81.0\"",
        "192.168.1.15 - admin [20/Jun/2026:01:24:12 +0000] \"POST /admin/login HTTP/1.1\" 401 1024 \"https://app.com/login\"",
        "DEBUG:root:Connecting to database pool size=20...",
        "ERROR:database:Connection pool exhausted after 30000ms. Aborting transaction."
    ]
    
    gibberish_and_scraps = [
        "asdfghjkl;",
        "1234567890qwertyuiop",
        "---",
        "...",
        "null",
        "undefined",
        "[]",
        "{}",
        "N/A",
        "hello hello hello hello hello hello hello hello"
    ]
    
    off_topic_spam = [
        "Hey! Buy cheap watches at http://cheapwatches-deals.biz !!! Great discounts!",
        "Special offer: get rich quick with our cryptocurrency trading bot, visit free-crypto-link.com",
        "Shopping list for the weekend: apples, milk, whole wheat bread, laundry detergent, eggs",
        "The quick brown fox jumps over the lazy dog."
    ]
    
    # Combine everything to simulate raw, dirty logs/feedback/scrapes
    # We want a mix where ~70% is clean and 30% is noise
    dataset = []
    
    # 60 clean samples
    for _ in range(60):
        dataset.append(random.choice(valid_intents))
        
    # 10 malicious
    for _ in range(10):
        dataset.append(random.choice(malicious_inputs))
        
    # 10 logs/tracebacks
    for _ in range(10):
        dataset.append(random.choice(system_noise))
        
    # 10 gibberish
    for _ in range(10):
        dataset.append(random.choice(gibberish_and_scraps))
        
    # 10 off-topic/spam
    for _ in range(10):
        dataset.append(random.choice(off_topic_spam))
        
    # Shuffle the dataset so noise is mixed in randomly
    random.shuffle(dataset)
    
    return dataset
