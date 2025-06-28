-- CCTNS Database Schema for Hackathon
-- Andhra Pradesh Police Department

-- District Master Table
CREATE TABLE DISTRICT_MASTER (
    district_id NUMBER(10) PRIMARY KEY,
    district_code VARCHAR2(10) UNIQUE NOT NULL,
    district_name VARCHAR2(100) NOT NULL,
    region VARCHAR2(50),
    created_date DATE DEFAULT SYSDATE
);

-- Station Master Table
CREATE TABLE STATION_MASTER (
    station_id NUMBER(10) PRIMARY KEY,
    station_name VARCHAR2(100) NOT NULL,
    station_code VARCHAR2(20) UNIQUE NOT NULL,
    district_id NUMBER(10) NOT NULL,
    address VARCHAR2(500),
    phone VARCHAR2(20),
    created_date DATE DEFAULT SYSDATE,
    FOREIGN KEY (district_id) REFERENCES DISTRICT_MASTER(district_id)
);

-- Officer Master Table
CREATE TABLE OFFICER_MASTER (
    officer_id NUMBER(10) PRIMARY KEY,
    officer_name VARCHAR2(100) NOT NULL,
    badge_number VARCHAR2(20) UNIQUE NOT NULL,
    rank VARCHAR2(50),
    station_id NUMBER(10) NOT NULL,
    phone VARCHAR2(20),
    email VARCHAR2(100),
    join_date DATE,
    status VARCHAR2(20) DEFAULT 'ACTIVE',
    created_date DATE DEFAULT SYSDATE,
    FOREIGN KEY (station_id) REFERENCES STATION_MASTER(station_id)
);

-- Crime Type Master Table
CREATE TABLE CRIME_TYPE_MASTER (
    crime_type_id NUMBER(10) PRIMARY KEY,
    crime_code VARCHAR2(20) UNIQUE NOT NULL,
    description VARCHAR2(200) NOT NULL,
    category VARCHAR2(50),
    severity_level NUMBER(1) CHECK (severity_level BETWEEN 1 AND 5),
    created_date DATE DEFAULT SYSDATE
);

-- FIR (First Information Report) Table
CREATE TABLE FIR (
    fir_id NUMBER(10) PRIMARY KEY,
    fir_number VARCHAR2(50) UNIQUE NOT NULL,
    district_id NUMBER(10) NOT NULL,
    station_id NUMBER(10) NOT NULL,
    crime_type_id NUMBER(10) NOT NULL,
    incident_date DATE NOT NULL,
    incident_time TIMESTAMP,
    incident_location VARCHAR2(500),
    complainant_name VARCHAR2(100),
    complainant_phone VARCHAR2(20),
    description CLOB,
    status VARCHAR2(20) DEFAULT 'REGISTERED',
    investigating_officer_id NUMBER(10),
    registered_date DATE DEFAULT SYSDATE,
    FOREIGN KEY (district_id) REFERENCES DISTRICT_MASTER(district_id),
    FOREIGN KEY (station_id) REFERENCES STATION_MASTER(station_id),
    FOREIGN KEY (crime_type_id) REFERENCES CRIME_TYPE_MASTER(crime_type_id),
    FOREIGN KEY (investigating_officer_id) REFERENCES OFFICER_MASTER(officer_id)
);

-- Arrest Records Table
CREATE TABLE ARREST (
    arrest_id NUMBER(10) PRIMARY KEY,
    arrest_number VARCHAR2(50) UNIQUE NOT NULL,
    fir_id NUMBER(10) NOT NULL,
    arrested_person_name VARCHAR2(100) NOT NULL,
    arrested_person_age NUMBER(3),
    arrested_person_address VARCHAR2(500),
    arrest_date DATE NOT NULL,
    arrest_time TIMESTAMP,
    arresting_officer_id NUMBER(10) NOT NULL,
    arrest_location VARCHAR2(500),
    charges VARCHAR2(1000),
    status VARCHAR2(20) DEFAULT 'ARRESTED',
    created_date DATE DEFAULT SYSDATE,
    FOREIGN KEY (fir_id) REFERENCES FIR(fir_id),
    FOREIGN KEY (arresting_officer_id) REFERENCES OFFICER_MASTER(officer_id)
);

-- Indexes for better performance
CREATE INDEX idx_fir_incident_date ON FIR(incident_date);
CREATE INDEX idx_fir_status ON FIR(status);
CREATE INDEX idx_arrest_date ON ARREST(arrest_date);
CREATE INDEX idx_officer_station ON OFFICER_MASTER(station_id);

-- Sequences for auto-increment
CREATE SEQUENCE district_seq START WITH 1 INCREMENT BY 1;
CREATE SEQUENCE station_seq START WITH 1 INCREMENT BY 1;
CREATE SEQUENCE officer_seq START WITH 1 INCREMENT BY 1;
CREATE SEQUENCE crime_type_seq START WITH 1 INCREMENT BY 1;
CREATE SEQUENCE fir_seq START WITH 1 INCREMENT BY 1;
CREATE SEQUENCE arrest_seq START WITH 1 INCREMENT BY 1;