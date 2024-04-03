CREATE TABLE IF NOT EXISTS client (
    id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    valid BOOLEAN NOT NULL DEFAULT true
);


INSERT INTO client VALUES 
('sample-client','sample-client',TRUE),
('sample-client-2','sample-client-2',TRUE),
('sample-client-3','sample-client-3',TRUE);
