drop table if exists attendance;

-- the following types are from the system.
-- att_type: 1=Fingerprint (F), 
-- att_punch: 1=Check-In or 0=Check-Out
-- att_status: 0=Failed or 1=Success

create table attendance (
    id integer primary key autoincrement,
    staff integer not null,
    att_date text not null,
    att_time text not null,
    att_punch integer,
    unique (staff, att_date, att_time)
);

drop table if exists original_data;

create table original_data (
    id integer primary key autoincrement,
    staff integer not null references staff (staff),
    att_date text not null,
    att_time text not null,
    att_punch int not null,
    att_status int not null default 1,
    unique (staff, att_date, att_time)
);