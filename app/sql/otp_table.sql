drop table if exists otp;

CREATE TABLE otp (
    id integer primary key,
    userid integer not null references users (id),
    otp varchar(6) not null,
    otp_time datetime not null,
    valid boolean not null default 0
);