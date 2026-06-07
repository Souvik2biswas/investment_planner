'use client';

import { useState, useEffect, useRef } from 'react';
import { 
  UploadCloud, 
  Send, 
  TrendingUp, 
  ArrowUpRight, 
  ArrowDownRight, 
  Sparkles, 
  FileText, 
  PieChart, 
  Shield, 
  Trash2, 
  User, 
  Cpu, 
  Code, 
  RefreshCw,
  Search,
  Wallet
} from 'lucide-react';
import { getMockSession, setMockSession, MOCK_USERS } from './lib/supabase';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function Home() {
  const [currentUser, setCurrentUser] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [taxAdvice, setTaxAdvice] = useState({ summary: '', recommendations: [] });
  const [chatHistory, setChatHistory] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [isChatLoading, setIsChatLoading] = useState(false);
  
  // Search and Filter States
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('ALL');
  
  const fileInputRef = useRef(null);
  const chatEndRef = useRef(null);
  
  // Load user session on mount
  useEffect(() => {
    const session = getMockSession();
    setCurrentUser(session);
  }, []);

  // Fetch transactions and tax advice whenever active user changes
  useEffect(() => {
    if (currentUser) {
      fetchUserData();
      // Reset Chat
      setChatHistory([
        {
          role: 'assistant',
          content: `Hello ${currentUser.name}! I am your Autonomous Financial Co-Pilot. I have established a secure environment for your bank statements. Upload your PDF to categorize your transactions, execute mathematically perfect spending SQL queries, or analyze tax deductions. How can I help you today?`
        }
      ]);
    }
  }, [currentUser]);

  // Scroll chat window to bottom
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatHistory, isChatLoading]);

  const fetchUserData = async () => {
    if (!currentUser) return;
    try {
      // Get Transactions
      const txRes = await fetch(`${API_URL}/api/transactions?user_id=${currentUser.id}`);
      if (txRes.ok) {
        const txData = await txRes.json();
        setTransactions(txData);
      }
      
      // Get Tax Advice
      const taxRes = await fetch(`${API_URL}/api/tax-advice?user_id=${currentUser.id}`);
      if (taxRes.ok) {
        const taxData = await taxRes.json();
        setTaxAdvice(taxData);
      }
    } catch (err) {
      console.error("Failed to connect to backend api:", err);
    }
  };

  const handleUserChange = (e) => {
    const selected = MOCK_USERS.find(u => u.id === e.target.value);
    if (selected) {
      setCurrentUser(selected);
      setMockSession(selected);
    }
  };

  const triggerUploadClick = () => {
    fileInputRef.current.click();
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);
    formData.append('user_id', currentUser.id);

    setIsUploading(true);
    try {
      const response = await fetch(`${API_URL}/api/upload-statement`, {
        method: 'POST',
        body: formData,
      });

      if (response.ok) {
        const result = await response.json();
        // Add chat feedback
        setChatHistory(prev => [
          ...prev,
          {
            role: 'assistant',
            content: `Successfully parsed your bank statement: **${result.filename}**. Identified **${result.transactions_parsed}** transaction records, masked account details locally, and classified them into respective categories. Click refresh to load them into your panel!`
          }
        ]);
        await fetchUserData();
      } else {
        const errData = await response.json();
        alert(`Failed to parse bank statement: ${errData.detail || 'Error'}`);
      }
    } catch (err) {
      console.error(err);
      alert("Error contacting the statement parsing backend.");
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleSendMessage = async (textToSend = inputMessage) => {
    const cleanedText = textToSend.trim();
    if (!cleanedText) return;

    setChatHistory(prev => [...prev, { role: 'user', content: cleanedText }]);
    setInputMessage('');
    setIsChatLoading(true);

    try {
      const response = await fetch(`${API_URL}/api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: currentUser.id,
          message: cleanedText,
          history: chatHistory.map(m => ({ role: m.role, content: m.content }))
        })
      });

      if (response.ok) {
        const data = await response.json();
        setChatHistory(prev => [
          ...prev,
          {
            role: 'assistant',
            content: data.response,
            sql_query: data.sql_query,
            agent_used: data.agent_used,
            query_data: data.data
          }
        ]);
        // Refresh local data in case categories or details updated
        if (cleanedText.toLowerCase().includes("upload") || cleanedText.toLowerCase().includes("parse")) {
          fetchUserData();
        }
      } else {
        setChatHistory(prev => [
          ...prev,
          { role: 'assistant', content: "I encountered an orchestrator network error. Please ensure the backend is running." }
        ]);
      }
    } catch (err) {
      console.error(err);
      setChatHistory(prev => [
        ...prev,
        { role: 'assistant', content: "Failed to connect to the backend agent server. Please run `uvicorn backend.app.main:app`." }
      ]);
    } finally {
      setIsChatLoading(false);
    }
  };

  const clearAllTransactions = async () => {
    if (!confirm("Are you sure you want to clear all transactions? This will erase mock data for this user ID.")) return;
    try {
      const response = await fetch(`${API_URL}/api/clear-transactions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: `user_id=${currentUser.id}`
      });
      if (response.ok) {
        setTransactions([]);
        setTaxAdvice({ summary: '', recommendations: [] });
        setChatHistory(prev => [
          ...prev,
          { role: 'assistant', content: "Successfully cleared your financial database ledger. Ready for a clean upload." }
        ]);
      }
    } catch (err) {
      console.error(err);
    }
  };

  // Quick statistics calculation
  const totalDebit = transactions
    .filter(t => t.transaction_type === 'DEBIT')
    .reduce((sum, t) => sum + t.amount, 0);

  const totalCredit = transactions
    .filter(t => t.transaction_type === 'CREDIT')
    .reduce((sum, t) => sum + t.amount, 0);

  const netBalance = totalCredit - totalDebit;

  const potentialDeductions = transactions
    .filter(t => t.category === 'POTENTIAL_DEDUCTION' || t.notes?.toLowerCase().includes("deduction"))
    .reduce((sum, t) => sum + t.amount, 0);

  // SVG Chart Computations (Category breakdown)
  const categorySummary = transactions
    .filter(t => t.transaction_type === 'DEBIT')
    .reduce((acc, t) => {
      acc[t.category] = (acc[t.category] || 0) + t.amount;
      return acc;
    }, {});

  const totalSpend = Object.values(categorySummary).reduce((a, b) => a + b, 0);

  const chartData = Object.entries(categorySummary).map(([cat, val]) => ({
    category: cat,
    amount: val,
    percentage: totalSpend > 0 ? (val / totalSpend) * 100 : 0
  })).sort((a, b) => b.amount - a.amount);

  // Filter Transactions for Display Table
  const filteredTransactions = transactions.filter(t => {
    const matchesSearch = t.description.toLowerCase().includes(searchTerm.toLowerCase()) || 
                          t.category.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesCat = selectedCategory === 'ALL' || t.category === selectedCategory;
    return matchesSearch && matchesCat;
  });

  // Color mapper for categories
  const getCategoryColor = (cat) => {
    switch (cat) {
      case 'FOOD': return '#FF9800';
      case 'UTILITIES': return '#2196F3';
      case 'RENT': return '#9C27B0';
      case 'TRAVEL': return '#00BCD4';
      case 'ENTERTAINMENT': return '#E91E63';
      case 'BUSINESS_EXPENSE': return '#00E676';
      case 'SALARY': return '#4CAF50';
      case 'INVESTMENT': return '#3F51B5';
      case 'POTENTIAL_DEDUCTION': return '#FFEE58';
      default: return '#9E9E9E';
    }
  };

  return (
    <div className="flex flex-col min-h-screen bg-[#080A10]">
      
      {/* Header bar */}
      <header className="glass-card m-4 px-6 py-4 flex flex-wrap items-center justify-between gap-4" style={{ borderRadius: '12px' }}>
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-gradient-to-tr from-[#00F2FE] to-[#4FACFE] rounded-xl text-black">
            <Wallet size={22} className="animate-pulse" />
          </div>
          <div>
            <h1 className="text-xl font-extrabold text-white tracking-tight flex items-center gap-2">
              APEX <span className="text-gradient font-light">FINANCE AGENT</span>
            </h1>
            <p className="text-[11px] text-[#64748B] font-mono uppercase tracking-widest">Autonomous Financial Copilot</p>
          </div>
        </div>

        {/* User context switcher (demonstrating isolation / row-level security) */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 bg-[#121829] px-3 py-1.5 rounded-lg border border-white/5">
            <User size={14} className="text-[#00F2FE]" />
            <select 
              value={currentUser?.id || ''} 
              onChange={handleUserChange}
              className="bg-transparent text-xs font-semibold text-white outline-none border-none cursor-pointer"
            >
              {MOCK_USERS.map(u => (
                <option key={u.id} value={u.id} className="bg-[#0E121E] text-white">
                  {u.name} ({u.role})
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-2">
            <button 
              onClick={fetchUserData}
              className="p-2.5 bg-white/5 hover:bg-white/10 text-white rounded-lg border border-white/5 transition-all"
              title="Refresh ledger state"
            >
              <RefreshCw size={14} />
            </button>
            <button 
              onClick={clearAllTransactions}
              className="p-2.5 bg-red-500/10 hover:bg-red-500/20 text-red-400 rounded-lg border border-red-500/10 transition-all"
              title="Clear all transactions"
            >
              <Trash2 size={14} />
            </button>
          </div>
        </div>
      </header>

      {/* Main Grid Panel */}
      <main className="flex-1 px-4 pb-6 grid grid-cols-1 lg:grid-cols-12 gap-5">
        
        {/* Left Control Center (70% width on large screen) */}
        <section className="lg:col-span-8 flex flex-col gap-5">
          
          {/* Quick Metrics stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            
            <div className="glass-card p-4 flex flex-col gap-1.5 relative overflow-hidden">
              <span className="text-xs text-[#94A3B8] font-semibold">Total Inflow</span>
              <span className="text-lg font-bold text-[#00E676] font-mono">₹{totalCredit.toLocaleString('en-IN')}</span>
              <div className="absolute right-3 top-3 text-[#00E676]/20"><ArrowUpRight size={24} /></div>
            </div>

            <div className="glass-card p-4 flex flex-col gap-1.5 relative overflow-hidden">
              <span className="text-xs text-[#94A3B8] font-semibold">Total Outflow</span>
              <span className="text-lg font-bold text-[#FF1744] font-mono">₹{totalDebit.toLocaleString('en-IN')}</span>
              <div className="absolute right-3 top-3 text-[#FF1744]/20"><ArrowDownRight size={24} /></div>
            </div>

            <div className="glass-card p-4 flex flex-col gap-1.5 relative overflow-hidden">
              <span className="text-xs text-[#94A3B8] font-semibold">Net Balance</span>
              <span className={`text-lg font-bold font-mono ${netBalance >= 0 ? 'text-[#00F2FE]' : 'text-red-400'}`}>
                ₹{netBalance.toLocaleString('en-IN')}
              </span>
              <div className="absolute right-3 top-3 text-[#00F2FE]/20"><TrendingUp size={24} /></div>
            </div>

            <div className="glass-card p-4 flex flex-col gap-1.5 relative overflow-hidden border-yellow-500/10">
              <span className="text-xs text-[#94A3B8] font-semibold">Tax Saving Identified</span>
              <span className="text-lg font-bold text-yellow-400 font-mono">₹{potentialDeductions.toLocaleString('en-IN')}</span>
              <div className="absolute right-3 top-3 text-yellow-400/20"><Sparkles size={24} /></div>
            </div>

          </div>

          {/* Core visualizer block (PDF parser upload & SVG Chart breakdown) */}
          <div className="grid grid-cols-1 md:grid-cols-12 gap-5">
            
            {/* Bank Statement Upload Center */}
            <div className="glass-card p-5 md:col-span-5 flex flex-col items-center justify-center text-center gap-4 min-h-[200px]">
              <div className="p-4 bg-white/5 rounded-2xl border border-white/5 text-[#00F2FE] relative">
                <UploadCloud size={40} className={isUploading ? "animate-bounce" : ""} />
              </div>
              <div>
                <h3 className="text-sm font-bold text-white">Upload Statement Ledger</h3>
                <p className="text-[11px] text-[#94A3B8] max-w-[200px] mt-1 leading-relaxed">
                  Support structured bank statements PDF. Masked & categorized locally.
                </p>
              </div>
              <input 
                type="file" 
                ref={fileInputRef} 
                onChange={handleFileUpload} 
                className="hidden" 
                accept=".pdf" 
              />
              <button 
                onClick={triggerUploadClick}
                disabled={isUploading}
                className="w-full py-2 bg-gradient-to-r from-[#00F2FE] to-[#4FACFE] text-black text-xs font-bold rounded-lg hover:shadow-lg transition-all active:scale-[0.98] disabled:opacity-50"
              >
                {isUploading ? "Scrubbing & Extracting..." : "Choose PDF File"}
              </button>
            </div>

            {/* SVG Visualizer breakdown charts */}
            <div className="glass-card p-5 md:col-span-7 flex flex-col justify-between gap-4">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-2">
                  <PieChart size={14} className="text-[#00F2FE]" /> Expenses Category Distribution
                </h3>
                <span className="text-[11px] text-[#64748B] font-mono">Debit Breakdown</span>
              </div>

              {chartData.length === 0 ? (
                <div className="flex-1 flex flex-col items-center justify-center text-center py-6 text-[#64748B] text-xs">
                  No transaction data available yet. Please upload a bank statement.
                </div>
              ) : (
                <div className="flex flex-col sm:flex-row items-center gap-6 py-2">
                  {/* Custom SVG Donut Chart */}
                  <div className="relative w-32 h-32 flex items-center justify-center">
                    <svg width="100%" height="100%" viewBox="0 0 42 42" className="transform -rotate-90">
                      <circle cx="21" cy="21" r="15.915" fill="transparent" stroke="#121829" strokeWidth="4" />
                      {(() => {
                        let accumulatedPercent = 0;
                        return chartData.map((item, idx) => {
                          const strokeDashArray = `${item.percentage} ${100 - item.percentage}`;
                          const strokeDashOffset = 100 - accumulatedPercent;
                          accumulatedPercent += item.percentage;
                          return (
                            <circle 
                              key={idx}
                              cx="21" 
                              cy="21" 
                              r="15.915" 
                              fill="transparent" 
                              stroke={getCategoryColor(item.category)} 
                              strokeWidth="4.5"
                              strokeDasharray={strokeDashArray}
                              strokeDashoffset={strokeDashOffset}
                              className="transition-all duration-500 ease-in-out"
                            />
                          );
                        });
                      })()}
                    </svg>
                    <div className="absolute flex flex-col items-center justify-center text-center">
                      <span className="text-[10px] text-[#94A3B8] font-bold">Total Spent</span>
                      <span className="text-xs font-extrabold text-white font-mono">₹{totalSpend.toLocaleString('en-IN')}</span>
                    </div>
                  </div>

                  {/* Legends */}
                  <div className="flex-1 flex flex-col gap-2 w-full">
                    {chartData.slice(0, 4).map((item, idx) => (
                      <div key={idx} className="flex items-center justify-between text-xs">
                        <div className="flex items-center gap-2">
                          <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: getCategoryColor(item.category) }} />
                          <span className="text-[#94A3B8] font-medium text-[11px]">{item.category}</span>
                        </div>
                        <span className="font-mono text-white text-[11px] font-bold">
                          {item.percentage.toFixed(1)}% (₹{item.amount.toLocaleString('en-IN')})
                        </span>
                      </div>
                    ))}
                    {chartData.length > 4 && (
                      <div className="text-[10px] text-[#64748B] text-right">
                        + {chartData.length - 4} other categories
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>

          </div>

          {/* Transaction Ledger Table with search and local category filter */}
          <div className="glass-card p-5 flex-1 flex flex-col gap-4">
            
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h3 className="text-sm font-bold text-white flex items-center gap-2">
                  <FileText size={16} className="text-[#00F2FE]" /> Financial Ledger
                </h3>
                <p className="text-[11px] text-[#64748B]">Audited and sanitized transaction logs</p>
              </div>

              {/* Filter tools */}
              <div className="flex items-center gap-2.5 flex-wrap">
                <div className="flex items-center gap-2 bg-[#121829] px-2.5 py-1.5 rounded-lg border border-white/5 text-xs text-[#94A3B8]">
                  <Search size={12} />
                  <input 
                    type="text" 
                    placeholder="Search desc..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="bg-transparent border-none outline-none text-white w-28 text-xs"
                  />
                </div>

                <select 
                  value={selectedCategory} 
                  onChange={(e) => setSelectedCategory(e.target.value)}
                  className="bg-[#121829] border border-white/5 rounded-lg text-xs font-semibold text-white px-2 py-1.5 outline-none cursor-pointer"
                >
                  <option value="ALL">All Categories</option>
                  <option value="FOOD">Food</option>
                  <option value="UTILITIES">Utilities</option>
                  <option value="RENT">Rent</option>
                  <option value="TRAVEL">Travel</option>
                  <option value="ENTERTAINMENT">Entertainment</option>
                  <option value="BUSINESS_EXPENSE">Business</option>
                  <option value="SALARY">Salary</option>
                  <option value="INVESTMENT">Investment</option>
                  <option value="POTENTIAL_DEDUCTION">Tax Deductions</option>
                  <option value="OTHERS">Others</option>
                </select>
              </div>
            </div>

            {/* Table Area */}
            <div className="overflow-x-auto max-h-[400px] border border-white/5 rounded-xl">
              {filteredTransactions.length === 0 ? (
                <div className="text-center py-12 text-xs text-[#64748B]">
                  No transactions found matching criteria. Upload a statement to load data.
                </div>
              ) : (
                <table className="finance-table">
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>Description</th>
                      <th>Category</th>
                      <th className="text-right">Amount</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredTransactions.map((tx, idx) => (
                      <tr key={idx} className="hover:bg-white/[0.01]">
                        <td className="text-xs font-mono text-[#94A3B8]">{tx.transaction_date}</td>
                        <td className="max-w-[200px] truncate text-xs font-semibold text-white">
                          <div className="flex flex-col gap-0.5">
                            <span>{tx.description}</span>
                            {tx.notes && (
                              <span className="text-[10px] text-yellow-400 font-light italic flex items-center gap-1">
                                <Sparkles size={8} /> {tx.notes}
                              </span>
                            )}
                          </div>
                        </td>
                        <td>
                          <span className={`badge badge-${tx.category.toLowerCase().replace('_', '')}`}>
                            {tx.category}
                          </span>
                        </td>
                        <td className={`text-right font-mono text-xs font-bold ${tx.transaction_type === 'CREDIT' ? 'text-[#00E676]' : 'text-[#FF1744]'}`}>
                          {tx.transaction_type === 'CREDIT' ? '+' : '-'} ₹{tx.amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>

        </section>

        {/* Right Financial Co-Pilot Chat System (30% width) */}
        <section className="lg:col-span-4 glass-card p-4 flex flex-col h-[700px] lg:h-auto min-h-[500px]">
          
          {/* Header */}
          <div className="flex items-center justify-between pb-3 border-bottom border-white/5">
            <div className="flex items-center gap-2">
              <Cpu size={16} className="text-[#00F2FE] animate-pulse" />
              <div>
                <h3 className="text-xs font-bold text-white uppercase tracking-wider">Financial Co-Pilot</h3>
                <p className="text-[9px] text-[#64748B]">Dual Mode AI: Probabilistic & SQL</p>
              </div>
            </div>
            <div className="flex items-center gap-1 text-[9px] bg-[#121829] px-2 py-1 rounded border border-white/5 text-yellow-400 font-bold">
              <Shield size={10} /> RLS ACTIVE
            </div>
          </div>

          {/* Messages body */}
          <div className="flex-1 overflow-y-auto py-3 space-y-4 pr-1">
            {chatHistory.map((msg, idx) => (
              <div 
                key={idx} 
                className={`flex flex-col gap-1 max-w-[90%] ${msg.role === 'user' ? 'ml-auto items-end' : 'mr-auto items-start'}`}
              >
                {/* Bubble */}
                <div 
                  className={`p-3 rounded-2xl text-xs leading-relaxed ${
                    msg.role === 'user' 
                      ? 'bg-gradient-to-tr from-[#00F2FE] to-[#4FACFE] text-black font-semibold rounded-tr-none' 
                      : 'bg-[#121829] text-white border border-white/5 rounded-tl-none'
                  }`}
                >
                  {/* Handle formatting for markdown bold */}
                  {msg.content.split('\n').map((line, lIdx) => {
                    // Quick conversion of **text** to <strong>text</strong>
                    const parts = line.split('**');
                    return (
                      <p key={lIdx} className="mb-1.5 last:mb-0">
                        {parts.map((part, pIdx) => pIdx % 2 === 1 ? <strong key={pIdx} className="font-extrabold text-[#00F2FE]">{part}</strong> : part)}
                      </p>
                    );
                  })}

                  {/* If SQL was executed by SQL Agent, display the query bubble */}
                  {msg.sql_query && (
                    <div className="mt-3 p-2 bg-black/60 border border-white/10 rounded-lg font-mono text-[9px] text-green-400 overflow-x-auto flex flex-col gap-1.5">
                      <div className="flex items-center justify-between text-[#94A3B8] border-b border-white/5 pb-1">
                        <span className="flex items-center gap-1 uppercase tracking-wider font-bold text-[8px]"><Code size={10} /> SQL Query Executed</span>
                        <span className="text-[7px]">Deterministic Math</span>
                      </div>
                      <code>{msg.sql_query}</code>
                    </div>
                  )}
                </div>
                
                {/* Agent label */}
                <span className="text-[8px] text-[#64748B] uppercase tracking-widest font-mono">
                  {msg.role === 'user' ? 'You' : `${msg.agent_used || 'system'} co-pilot`}
                </span>
              </div>
            ))}

            {isChatLoading && (
              <div className="mr-auto items-start max-w-[80%] flex flex-col gap-1">
                <div className="p-3 bg-[#121829] border border-white/5 rounded-2xl rounded-tl-none flex items-center gap-2 text-xs text-[#94A3B8]">
                  <RefreshCw size={12} className="animate-spin text-[#00F2FE]" />
                  <span>Thinking... executing database operations...</span>
                </div>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          {/* Quick preset action chips */}
          <div className="py-2.5 flex flex-wrap gap-1.5 border-t border-white/5">
            <button 
              onClick={() => handleSendMessage("What is my average monthly spend on utilities?")}
              className="px-2.5 py-1 bg-white/5 hover:bg-white/10 rounded-full text-[10px] text-white/80 border border-white/5 transition-all"
            >
              Avg Utilities Spend
            </button>
            <button 
              onClick={() => handleSendMessage("Show me my software subscriptions and potential business deductions.")}
              className="px-2.5 py-1 bg-white/5 hover:bg-white/10 rounded-full text-[10px] text-white/80 border border-white/5 transition-all"
            >
              SaaS / SaaS Deductions
            </button>
            <button 
              onClick={() => handleSendMessage("Provide my tax recommendations under Section 80C and 80D.")}
              className="px-2.5 py-1 bg-white/5 hover:bg-white/10 rounded-full text-[10px] text-white/80 border border-white/5 transition-all"
            >
              Tax Advisory
            </button>
          </div>

          {/* Input text send area */}
          <div className="flex gap-2 pt-2 border-t border-white/5">
            <input 
              type="text" 
              placeholder="Ask SQL Agent or Tax advisor..."
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
              className="flex-1 input-glass"
              style={{ padding: '8px 12px', borderRadius: '8px' }}
            />
            <button 
              onClick={() => handleSendMessage()}
              disabled={isChatLoading || !inputMessage.trim()}
              className="p-2.5 bg-gradient-to-tr from-[#00F2FE] to-[#4FACFE] hover:shadow-lg text-black rounded-lg transition-all active:scale-[0.96] disabled:opacity-40"
            >
              <Send size={14} />
            </button>
          </div>

        </section>

      </main>
    </div>
  );
}
