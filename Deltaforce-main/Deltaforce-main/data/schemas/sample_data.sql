-- Sample Data for CCTNS Database
-- For Hackathon Demo Purposes

-- Insert Districts
INSERT INTO DISTRICT_MASTER VALUES (1, 'GTR', 'Guntur', 'Coastal Andhra', SYSDATE);
INSERT INTO DISTRICT_MASTER VALUES (2, 'VJA', 'Vijayawada', 'Coastal Andhra', SYSDATE);
INSERT INTO DISTRICT_MASTER VALUES (3, 'VSP', 'Visakhapatnam', 'Coastal Andhra', SYSDATE);
INSERT INTO DISTRICT_MASTER VALUES (4, 'TPT', 'Tirupati', 'Rayalaseema', SYSDATE);
INSERT INTO DISTRICT_MASTER VALUES (5, 'KNL', 'Kurnool', 'Rayalaseema', SYSDATE);

-- Insert Police Stations
INSERT INTO STATION_MASTER VALUES (1, 'Guntur Town Police Station', 'GTR_TOWN', 1, 'Main Road, Guntur', '0863-2234567', SYSDATE);
INSERT INTO STATION_MASTER VALUES (2, 'Vijayawada Central Police Station', 'VJA_CENTRAL', 2, 'MG Road, Vijayawada', '0866-2567890', SYSDATE);
INSERT INTO STATION_MASTER VALUES (3, 'Visakhapatnam Port Police Station', 'VSP_PORT', 3, 'Port Area, Visakhapatnam', '0891-2345678', SYSDATE);
INSERT INTO STATION_MASTER VALUES (4, 'Tirupati Temple Police Station', 'TPT_TEMPLE', 4, 'Temple Street, Tirupati', '0877-2234567', SYSDATE);
INSERT INTO STATION_MASTER VALUES (5, 'Kurnool City Police Station', 'KNL_CITY', 5, 'City Center, Kurnool', '08518-234567', SYSDATE);

-- Insert Officers
INSERT INTO OFFICER_MASTER VALUES (1, 'Inspector Ravi Kumar', 'AP001', 'Inspector', 1, '9876543210', 'ravi.kumar@appolice.gov.in', DATE '2020-01-15', 'ACTIVE', SYSDATE);
INSERT INTO OFFICER_MASTER VALUES (2, 'SI Priya Sharma', 'AP002', 'Sub Inspector', 1, '9876543211', 'priya.sharma@appolice.gov.in', DATE '2021-03-20', 'ACTIVE', SYSDATE);
INSERT INTO OFFICER_MASTER VALUES (3, 'Inspector Vikram Singh', 'AP003', 'Inspector', 2, '9876543212', 'vikram.singh@appolice.gov.in', DATE '2019-06-10', 'ACTIVE', SYSDATE);
INSERT INTO OFFICER_MASTER VALUES (4, 'ASI Lakshmi Devi', 'AP004', 'Assistant Sub Inspector', 3, '9876543213', 'lakshmi.devi@appolice.gov.in', DATE '2022-01-05', 'ACTIVE', SYSDATE);
INSERT INTO OFFICER_MASTER VALUES (5, 'Constable Rajesh Reddy', 'AP005', 'Police Constable', 4, '9876543214', 'rajesh.reddy@appolice.gov.in', DATE '2023-02-15', 'ACTIVE', SYSDATE);

-- Insert Crime Types
INSERT INTO CRIME_TYPE_MASTER VALUES (1, 'THF', 'Theft', 'Property Crime', 2, SYSDATE);
INSERT INTO CRIME_TYPE_MASTER VALUES (2, 'ROB', 'Robbery', 'Violent Crime', 4, SYSDATE);
INSERT INTO CRIME_TYPE_MASTER VALUES (3, 'AST', 'Assault', 'Violent Crime', 3, SYSDATE);
INSERT INTO CRIME_TYPE_MASTER VALUES (4, 'BRG', 'Burglary', 'Property Crime', 3, SYSDATE);
INSERT INTO CRIME_TYPE_MASTER VALUES (5, 'FRD', 'Fraud', 'White Collar Crime', 2, SYSDATE);
INSERT INTO CRIME_TYPE_MASTER VALUES (6, 'CYB', 'Cyber Crime', 'Cyber Crime', 2, SYSDATE);
INSERT INTO CRIME_TYPE_MASTER VALUES (7, 'DRG', 'Drug Trafficking', 'Narcotics', 5, SYSDATE);

-- Insert FIRs (Recent data for better demo)
INSERT INTO FIR VALUES (1, 'GTR/2025/000001', 1, 1, 1, DATE '2025-01-15', TIMESTAMP '2025-01-15 10:30:00', 'Market Area, Guntur', 'Ramesh Kumar', '9123456789', 'Mobile phone theft from shop', 'UNDER_INVESTIGATION', 1, SYSDATE);
INSERT INTO FIR VALUES (2, 'GTR/2025/000002', 1, 1, 3, DATE '2025-01-16', TIMESTAMP '2025-01-16 14:20:00', 'Bus Stand, Guntur', 'Sunita Devi', '9123456790', 'Physical assault case', 'REGISTERED', 2, SYSDATE);
INSERT INTO FIR VALUES (3, 'VJA/2025/000001', 2, 2, 2, DATE '2025-01-17', TIMESTAMP '2025-01-17 09:15:00', 'Commercial Street, Vijayawada', 'Prakash Rao', '9123456791', 'Armed robbery at jewelry shop', 'UNDER_INVESTIGATION', 3, SYSDATE);
INSERT INTO FIR VALUES (4, 'VSP/2025/000001', 3, 3, 6, DATE '2025-01-18', TIMESTAMP '2025-01-18 16:45:00', 'IT Hub, Visakhapatnam', 'Tech Solutions Pvt Ltd', '9123456792', 'Online fraud and data breach', 'REGISTERED', 4, SYSDATE);
INSERT INTO FIR VALUES (5, 'TPT/2025/000001', 4, 4, 4, DATE '2025-01-19', TIMESTAMP '2025-01-19 11:30:00', 'Residential Area, Tirupati', 'Venkat Reddy', '9123456793', 'House burglary during night hours', 'UNDER_INVESTIGATION', 5, SYSDATE);

-- Insert more FIRs for this month (better analytics)
INSERT INTO FIR VALUES (6, 'GTR/2025/000003', 1, 1, 1, DATE '2025-01-20', TIMESTAMP '2025-01-20 08:20:00', 'College Road, Guntur', 'Student Union', '9123456794', 'Bicycle theft from college campus', 'REGISTERED', 1, SYSDATE);
INSERT INTO FIR VALUES (7, 'GTR/2025/000004', 1, 1, 5, DATE '2025-01-21', TIMESTAMP '2025-01-21 13:10:00', 'Bank Street, Guntur', 'ABC Bank', '9123456795', 'ATM card fraud case', 'UNDER_INVESTIGATION', 2, SYSDATE);
INSERT INTO FIR VALUES (8, 'VJA/2025/000002', 2, 2, 7, DATE '2025-01-22', TIMESTAMP '2025-01-22 19:30:00', 'Highway, Vijayawada', 'Highway Patrol', '9123456796', 'Drug possession during vehicle check', 'CHARGESHEET_FILED', 3, SYSDATE);

-- Insert Arrests
INSERT INTO ARREST VALUES (1, 'ARR/GTR/2025/001', 1, 'Thief Kumar', 25, 'Slum Area, Guntur', DATE '2025-01-16', TIMESTAMP '2025-01-16 18:00:00', 1, 'Hideout near market', 'IPC 379 - Theft', 'IN_CUSTODY', SYSDATE);
INSERT INTO ARREST VALUES (2, 'ARR/VJA/2025/001', 3, 'Robber Singh', 30, 'Unknown Address', DATE '2025-01-18', TIMESTAMP '2025-01-18 22:30:00', 3, 'Commercial Street, Vijayawada', 'IPC 392 - Robbery', 'IN_CUSTODY', SYSDATE);
INSERT INTO ARREST VALUES (3, 'ARR/VJA/2025/002', 8, 'Drug Dealer Raja', 28, 'Highway Lodge', DATE '2025-01-22', TIMESTAMP '2025-01-22 20:00:00', 3, 'Highway, Vijayawada', 'NDPS Act - Drug Trafficking', 'IN_CUSTODY', SYSDATE);

-- Add some data for today for better demo
INSERT INTO FIR VALUES (9, 'GTR/2025/000005', 1, 1, 1, SYSDATE, SYSTIMESTAMP, 'New Market, Guntur', 'Daily Demo User', '9999999999', 'Demo theft case for today', 'REGISTERED', 1, SYSDATE);
INSERT INTO FIR VALUES (10, 'VJA/2025/000003', 2, 2, 3, SYSDATE, SYSTIMESTAMP, 'Demo Location, Vijayawada', 'Demo Complainant', '8888888888', 'Demo assault case for today', 'REGISTERED', 3, SYSDATE);

COMMIT;