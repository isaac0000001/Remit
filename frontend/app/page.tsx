"use client";

import { useMemo, useState } from "react";
import {
  ArrowDownLeft,
  ArrowLeftRight,
  ArrowUpRight,
  Bell,
  CreditCard,
  Globe,
  Home,
  Plus,
  Send,
  Settings,
  ShieldCheck,
  Wallet,
} from "lucide-react";

const rates: Record<string, number> = {
  NGN: 1450,
  EUR: 0.92,
  GBP: 0.79,
};

const currencySymbols: Record<string, string> = {
  USD: "$",
  NGN: "₦",
  EUR: "€",
  GBP: "£",
};

const transactions = [
  {
    name: "Transfer to Nigeria",
    date: "Today · 10:42 AM",
    amount: "-$250.00",
    status: "Processing",
    icon: ArrowUpRight,
  },
  {
    name: "Wallet funding",
    date: "Yesterday · 2:15 PM",
    amount: "+$500.00",
    status: "Completed",
    icon: ArrowDownLeft,
  },
  {
    name: "Transfer to London",
    date: "Nov 3 · 11:30 AM",
    amount: "-$120.00",
    status: "Completed",
    icon: ArrowUpRight,
  },
];

export default function HomePage() {
  const [amount, setAmount] = useState("100");
  const [currency, setCurrency] = useState("NGN");
  const [message, setMessage] = useState("");

  const convertedAmount = useMemo(() => {
    const value = Number(amount);

    if (!Number.isFinite(value) || value < 0) {
      return "0.00";
    }

    return (value * rates[currency]).toLocaleString("en-US", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  }, [amount, currency]);

  function handleTransfer() {
    setMessage(
      "This is a demonstration. Live transfers are not enabled yet."
    );
  }

  return (
    <div className="dashboard">
      <aside className="sidebar">
        <div className="logo">
          REMIT<span>.</span>
        </div>

        <p className="nav-label">MENU</p>

        <nav>
          <a className="nav-item active" href="#">
            <Home size={17} /> Dashboard
          </a>

          <a className="nav-item" href="#send">
            <Send size={17} /> Send Money
          </a>

          <a className="nav-item" href="#transactions">
            <ArrowLeftRight size={17} /> Transactions
          </a>

          <a className="nav-item" href="#wallet">
            <Wallet size={17} /> Wallet
          </a>

          <a className="nav-item" href="#rates">
            <Globe size={17} /> Exchange Rates
          </a>

          <a className="nav-item" href="#settings">
            <Settings size={17} /> Settings
          </a>
        </nav>

        <div className="sidebar-bottom">
          <ShieldCheck size={20} />
          <p>Secure international payments.</p>
          <p>REMIT Financial Platform</p>
        </div>
      </aside>

      <main className="main">
        <header className="topbar">
          <div className="welcome">
            <h1>Welcome back!</h1>
            <p>Manage your money across borders.</p>
          </div>

          <div className="profile">
            <Bell size={21} />
            <div className="avatar">R</div>
            REMIT Customer
          </div>
        </header>

        <section className="grid">
          <div className="card balance-card" id="wallet">
            <p className="muted">Total wallet balance</p>

            <div className="balance">$12,450.00</div>

            <p className="muted">Illustrative demo balance</p>

            <div className="balance-actions">
              <button
                className="btn btn-primary"
                onClick={() =>
                  setMessage("Wallet funding is not enabled in this demo.")
                }
              >
                <Plus size={15} /> Add Money
              </button>

              <button
                className="btn btn-light"
                onClick={() =>
                  document
                    .getElementById("send")
                    ?.scrollIntoView({ behavior: "smooth" })
                }
              >
                <Send size={15} /> Send Money
              </button>
            </div>
          </div>

          <div className="card" id="rates">
            <h2 className="section-title">Exchange rates</h2>

            <div className="rate-row">
              <span>USD / NGN</span>
              <span className="rate-value">₦1,450.00</span>
            </div>

            <div className="rate-row">
              <span>USD / EUR</span>
              <span className="rate-value">€0.92</span>
            </div>

            <div className="rate-row">
              <span>USD / GBP</span>
              <span className="rate-value">£0.79</span>
            </div>

            <p className="muted" style={{ marginTop: 12 }}>
              Illustrative rates only. Not live market quotes.
            </p>
          </div>
        </section>

        <section className="card send-card" id="send">
          <h2 className="section-title">Send money internationally</h2>

          <p className="muted" style={{ marginBottom: 22 }}>
            Preview a conversion before initiating a transfer.
          </p>

          <div className="form-grid">
            <div className="field">
              <label>YOU SEND (USD)</label>
              <input
                type="number"
                min="0"
                step="0.01"
                value={amount}
                onChange={(event) => setAmount(event.target.value)}
                placeholder="Enter amount"
              />
            </div>

            <div className="field">
              <label>RECIPIENT RECEIVES</label>
              <select
                value={currency}
                onChange={(event) => setCurrency(event.target.value)}
              >
                <option value="NGN">Nigeria - NGN</option>
                <option value="EUR">Europe - EUR</option>
                <option value="GBP">United Kingdom - GBP</option>
              </select>
            </div>
          </div>

          <div
            style={{
              marginTop: 22,
              padding: 18,
              background: "#f4f9f7",
              borderRadius: 10,
            }}
          >
            <p className="muted">Estimated recipient amount</p>

            <h2 style={{ marginTop: 8, fontSize: 26 }}>
              {currencySymbols[currency]}
              {convertedAmount}
            </h2>

            <p className="muted" style={{ marginTop: 8 }}>
              Indicative conversion. Fees and final rates are not yet
              connected.
            </p>
          </div>

          <button className="send-button" onClick={handleTransfer}>
            Preview Transfer
          </button>

          {message && (
            <div className="demo-notice" role="status">
              {message}
            </div>
          )}

          <div className="demo-notice">
            DEMO ENVIRONMENT: This dashboard does not move money, charge
            customers, or connect to payment providers.
          </div>
        </section>

        <section className="card transactions" id="transactions">
          <h2 className="section-title">Recent transactions</h2>

          {transactions.map((transaction, index) => {
            const Icon = transaction.icon;

            return (
              <div className="transaction" key={index}>
                <div style={{ display: "flex", gap: 12 }}>
                  <div
                    style={{
                      width: 38,
                      height: 38,
                      borderRadius: 10,
                      background: "#eaf7f2",
                      color: "#13a879",
                      display: "grid",
                      placeItems: "center",
                    }}
                  >
                    <Icon size={19} />
                  </div>

                  <div>
                    <p className="transaction-name">
                      {transaction.name}
                    </p>

                    <p className="transaction-date">
                      {transaction.date}
                    </p>
                  </div>
                </div>

                <div style={{ textAlign: "right" }}>
                  <p style={{ fontWeight: 700 }}>
                    {transaction.amount}
                  </p>

                  <span className="status">{transaction.status}</span>
                </div>
              </div>
            );
          })}
        </section>

        <footer
          style={{
            textAlign: "center",
            padding: "25px 0",
            color: "#718096",
            fontSize: 12,
          }}
        >
          © 2026 REMIT. All rights reserved.
        </footer>
      </main>
    </div>
  );
}
