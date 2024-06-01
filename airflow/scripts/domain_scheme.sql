
CREATE SCHEMA IF NOT EXISTS analysis;

CREATE TABLE IF NOT EXISTS analysis.domain_registered (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    domain VARCHAR(255) NOT NULL
);

CREATE TABLE IF NOT EXISTS analysis.domain_results (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    domain_id UUID NOT NULL REFERENCES analysis.domain_registered(id),
    domain_result VARCHAR(255) NOT NULL,
    dt_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS analysis.url_analysis (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    domain_result_id UUID NOT NULL REFERENCES analysis.domain_results(id),
    url VARCHAR(255) NOT NULL,
    alive BOOLEAN,
    dt_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS analysis.domain_analysis (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    domain_result_id UUID NOT NULL REFERENCES analysis.domain_results(id),
    domain VARCHAR(255) NOT NULL,
    matchWebContent BOOLEAN,
    matchFavicon BOOLEAN,
    mx BOOLEAN,
    score INT,
    dt_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

select * from analysis.domain_registered dr; 

select * from analysis.domain_results ds; 


INSERT INTO analysis.domain_registered (domain) VALUES
('google.com'),
('example.com'),
('openai.com'),
('github.com'),
('stackoverflow.com'),
('microsoft.com'),
('apple.com'),
('amazon.com'),
('facebook.com'),
('linkedin.com'),
('twitter.com'),
('instagram.com'),
('netflix.com'),
('youtube.com'),
('wikipedia.org'),
('yahoo.com'),
('reddit.com'),
('pinterest.com'),
('quora.com'),
('baidu.com'),
('aliexpress.com'),
('bbc.com'),
('cnn.com'),
('nytimes.com');


-- Populate domain_results table with fake domains
-- google.com fake domains
INSERT INTO analysis.domain_results (domain_id, domain_result) VALUES
((SELECT id FROM analysis.domain_registered WHERE domain = 'google.com'), 'goggle.com'),
((SELECT id FROM analysis.domain_registered WHERE domain = 'google.com'), 'gooogle.com'),
((SELECT id FROM analysis.domain_registered WHERE domain = 'google.com'), 'googl3.com'),
((SELECT id FROM analysis.domain_registered WHERE domain = 'google.com'), 'goolge.com'),
((SELECT id FROM analysis.domain_registered WHERE domain = 'google.com'), 'go0gle.com');

-- example.com fake domains
INSERT INTO analysis.domain_results (domain_id, domain_result) VALUES
((SELECT id FROM analysis.domain_registered WHERE domain = 'example.com'), 'examp1e.com'),
((SELECT id FROM analysis.domain_registered WHERE domain = 'example.com'), 'exampel.com'),
((SELECT id FROM analysis.domain_registered WHERE domain = 'example.com'), 'exampel.com'),
((SELECT id FROM analysis.domain_registered WHERE domain = 'example.com'), 'exampl3.com'),
((SELECT id FROM analysis.domain_registered WHERE domain = 'example.com'), 'examp1e.com');

-- Add more fake domains
-- openai.com fake domains
INSERT INTO analysis.domain_results (domain_id, domain_result) VALUES
((SELECT id FROM analysis.domain_registered WHERE domain = 'openai.com'), '0penai.com'),
((SELECT id FROM analysis.domain_registered WHERE domain = 'openai.com'), 'openal.com'),
((SELECT id FROM analysis.domain_registered WHERE domain = 'openai.com'), 'openaii.com'),
((SELECT id FROM analysis.domain_registered WHERE domain = 'openai.com'), 'openaii.com'),
((SELECT id FROM analysis.domain_registered WHERE domain = 'openai.com'), 'op3nai.com');

-- Add similar blocks for each domain in the domain_registered table

-- Using the pattern to create more fake domains

DO
$$
DECLARE
    valid_domains TEXT[] := ARRAY[
        'google.com', 'example.com', 'openai.com', 'github.com', 'stackoverflow.com',
        'microsoft.com', 'apple.com', 'amazon.com', 'facebook.com', 'linkedin.com',
        'twitter.com', 'instagram.com', 'netflix.com', 'youtube.com', 'wikipedia.org',
        'yahoo.com', 'reddit.com', 'pinterest.com', 'quora.com', 'baidu.com',
        'aliexpress.com', 'bbc.com', 'cnn.com', 'nytimes.com'
    ];
    tlds TEXT[] := ARRAY['.com', '.net', '.org', '.co', '.us'];
    fake_domain TEXT;
    valid_domain TEXT;
    domain_id UUID;
BEGIN
    FOR valid_domain IN SELECT unnest(valid_domains)
    LOOP
        SELECT id INTO domain_id FROM analysis.domain_registered WHERE domain = valid_domain;
        FOR i IN 1..40 LOOP
            fake_domain := substring(md5(random()::text), 1, 10) || tlds[(random() * array_length(tlds, 1) + 1)::int];
            IF fake_domain IS NOT NULL THEN
                EXECUTE format('INSERT INTO analysis.domain_results (domain_id, domain_result) VALUES (%L, %L)', domain_id, fake_domain);
            END IF;
        END LOOP;
    END LOOP;
END
$$;