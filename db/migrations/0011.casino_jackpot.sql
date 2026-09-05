-- depends: 0010.casino_luck
ALTER TABLE casino_balance ADD COLUMN jackpot_spins INTEGER NOT NULL DEFAULT 0;
