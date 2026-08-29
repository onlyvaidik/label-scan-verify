import React, { useState, useEffect } from "react";
import axios from "axios";
import { useAuth } from "../context/AuthContext";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "";

export default function StatutoryRuleLibrary() {
  const { user, isSuperAdmin, isOfficer } = useAuth();
  const [rules, setRules] = useState([]);
  const [tableII, setTableII] = useState([]);
  const [search, setSearch] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("All");
  const [editingRule, setEditingRule] = useState(null);
  const [updateMsg, setUpdateMsg] = useState("");

  // Interactive Calculator State
  const [calcArea, setCalcArea] = useState(120);

  useEffect(() => {
    fetchRules();
  }, []);

  const fetchRules = async () => {
    try {
      const res = await axios.get(`${BACKEND_URL}/api/rules`, { withCredentials: true });
      setRules(res.data.rules || []);
      setTableII(res.data.table_ii_reference || []);
    } catch (e) {
      console.error("Rules load error:", e);
    }
  };

  const filteredRules = rules.filter((r) => {
    const matchSearch =
      r.rule_name.toLowerCase().includes(search.toLowerCase()) ||
      r.section.toLowerCase().includes(search.toLowerCase()) ||
      r.description.toLowerCase().includes(search.toLowerCase());
    const matchCat = selectedCategory === "All" || r.category === selectedCategory;
    return matchSearch && matchCat;
  });

  const handleSaveRuleUpdate = async () => {
    if (!editingRule) return;
    try {
      await axios.put(
        `${BACKEND_URL}/api/rules/${editingRule.rule_id}`,
        editingRule,
        { withCredentials: true }
      );
      setUpdateMsg("Rule configuration updated successfully!");
      setEditingRule(null);
      fetchRules();
      setTimeout(() => setUpdateMsg(""), 3000);
    } catch (e) {
      console.error("Update error:", e);
    }
  };

  return (
    <div className="p-8 space-y-6 bg-[#f5f7fb] min-h-[calc(100vh-64px)] font-sans">
      {/* Header */}
      <div className="border-b border-gray-200 pb-5">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-xs font-bold text-[#E88A1E] uppercase tracking-wider bg-amber-50 px-2.5 py-0.5 rounded border border-amber-200">
            Statutory Code & Gazettes
          </span>
          <span className="text-xs text-gray-500">• Legal Metrology (Packaged Commodities) Rules, 2011</span>
        </div>
        <h1 className="text-2xl font-black text-[#001255] tracking-tight">Statutory Rule Library & Standards</h1>
        <p className="text-xs text-gray-600 mt-1">
          Codified legal standards under the Legal Metrology Act, 2009, Rule 6 mandatory declarations, Table-II font minimums, and penalty clauses.
        </p>
      </div>

      {updateMsg && (
        <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-xl text-xs font-bold">
          {updateMsg}
        </div>
      )}

      {/* Table-II Font Size Reference & Interactive Calculator */}
      <div className="bg-white rounded-2xl p-6 border border-gray-100 shadow-sm space-y-4">
        <div className="flex items-center justify-between border-b border-gray-100 pb-3">
          <div>
            <h2 className="text-base font-bold text-[#001255] flex items-center gap-2">
              <span className="material-symbols-outlined text-purple-600">table_chart</span>
              <span>Table-II Minimum Height of Numerals & Letters (Rule 7)</span>
            </h2>
            <p className="text-xs text-gray-500">Statutory minimum font size thresholds based on Principal Display Panel (PDP) area</p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
          {/* Table-II Reference Matrix */}
          <div className="md:col-span-8 overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-gray-50 text-gray-500 uppercase font-bold border-b border-gray-200">
                  <th className="p-2.5">PDP Area Bracket</th>
                  <th className="p-2.5">Min. Numeral Height (General)</th>
                  <th className="p-2.5">Min. Numeral (Blown/Moulded)</th>
                  <th className="p-2.5">Min. Letter Height</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                <tr className={calcArea <= 50 ? "bg-amber-50/60 font-bold" : ""}>
                  <td className="p-2.5">Area ≤ 50 sq. cm</td>
                  <td className="p-2.5 text-[#001255]">1.0 mm</td>
                  <td className="p-2.5 text-gray-600">2.0 mm</td>
                  <td className="p-2.5 text-[#001255]">1.0 mm</td>
                </tr>
                <tr className={calcArea > 50 && calcArea <= 200 ? "bg-amber-50/60 font-bold" : ""}>
                  <td className="p-2.5">50 sq. cm &lt; Area ≤ 200 sq. cm</td>
                  <td className="p-2.5 text-[#001255]">2.0 mm</td>
                  <td className="p-2.5 text-gray-600">4.0 mm</td>
                  <td className="p-2.5 text-[#001255]">1.5 mm</td>
                </tr>
                <tr className={calcArea > 200 && calcArea <= 1000 ? "bg-amber-50/60 font-bold" : ""}>
                  <td className="p-2.5">200 sq. cm &lt; Area ≤ 1000 sq. cm</td>
                  <td className="p-2.5 text-[#001255]">4.0 mm</td>
                  <td className="p-2.5 text-gray-600">6.0 mm</td>
                  <td className="p-2.5 text-[#001255]">2.0 mm</td>
                </tr>
                <tr className={calcArea > 1000 ? "bg-amber-50/60 font-bold" : ""}>
                  <td className="p-2.5">Area &gt; 1000 sq. cm</td>
                  <td className="p-2.5 text-[#001255]">6.0 mm</td>
                  <td className="p-2.5 text-gray-600">8.0 mm</td>
                  <td className="p-2.5 text-[#001255]">3.0 mm</td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* Interactive Calculator */}
          <div className="md:col-span-4 bg-gray-50 p-4 rounded-xl border border-gray-200 space-y-3 text-xs">
            <h4 className="font-bold text-[#001255] uppercase">Live PDP Font Threshold Calculator</h4>
            <div>
              <label className="block text-gray-600 mb-1">Enter Package PDP Area (sq. cm):</label>
              <input
                type="number"
                value={calcArea}
                onChange={(e) => setCalcArea(parseFloat(e.target.value) || 0)}
                className="w-full bg-white border border-gray-200 rounded-lg p-2 font-bold text-sm"
              />
            </div>
            <div className="p-3 bg-white rounded-lg border border-blue-100 space-y-1">
              <p className="text-gray-500">Minimum Required Numeral Height:</p>
              <p className="text-lg font-black text-[#001255]">
                {calcArea <= 50 ? "1.0 mm" : calcArea <= 200 ? "2.0 mm" : calcArea <= 1000 ? "4.0 mm" : "6.0 mm"}
              </p>
              <p className="text-gray-500">Minimum Required Letter Height:</p>
              <p className="text-sm font-bold text-gray-800">
                {calcArea <= 50 ? "1.0 mm" : calcArea <= 200 ? "1.5 mm" : calcArea <= 1000 ? "2.0 mm" : "3.0 mm"}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Rules Directory Search & Filter */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="flex-1 relative">
          <span className="absolute left-3 top-2.5 material-symbols-outlined text-sm text-gray-400">search</span>
          <input
            type="text"
            data-testid="search-rules-input"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search Rule name, section, description, penalty clause..."
            className="w-full bg-white border border-gray-200 rounded-xl pl-9 pr-4 py-2 text-xs text-gray-800 shadow-sm"
          />
        </div>

        <select
          data-testid="rules-category-select"
          value={selectedCategory}
          onChange={(e) => setSelectedCategory(e.target.value)}
          className="bg-white border border-gray-200 rounded-xl px-4 py-2 text-xs text-gray-800 shadow-sm"
        >
          <option value="All">All Categories</option>
          <option value="Identity & Origin">Identity & Origin</option>
          <option value="Product Identification">Product Identification</option>
          <option value="Quantity & Measurement">Quantity & Measurement</option>
          <option value="Dates & Shelf Life">Dates & Shelf Life</option>
          <option value="Pricing & Taxation">Pricing & Taxation</option>
          <option value="Consumer Redressal">Consumer Redressal</option>
          <option value="Typography & Readability">Typography & Readability</option>
        </select>
      </div>

      {/* Rules Cards List */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {filteredRules.map((r) => (
          <div
            key={r.rule_id}
            data-testid={`rule-card-${r.rule_id}`}
            className="bg-white rounded-2xl p-5 border border-gray-100 shadow-sm space-y-3 relative hover:shadow-md transition-all"
          >
            <div className="flex items-center justify-between">
              <span className="font-mono text-xs font-bold text-[#001255] bg-blue-50 px-2 py-0.5 rounded">
                {r.section}
              </span>
              <span
                className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase ${
                  r.severity === "Critical"
                    ? "bg-red-100 text-red-800"
                    : r.severity === "Major"
                    ? "bg-amber-100 text-amber-800"
                    : "bg-blue-100 text-blue-800"
                }`}
              >
                {r.severity} Severity
              </span>
            </div>

            <h3 className="text-sm font-bold text-gray-900">{r.rule_name}</h3>
            <p className="text-xs text-gray-600 leading-relaxed">{r.description}</p>

            <div className="p-3 bg-red-50/50 rounded-xl border border-red-100 text-[11px] text-red-900">
              <b>Penalty Clause:</b> {r.penalty_clause}
            </div>

            {(isSuperAdmin || isOfficer) && (
              <div className="pt-2 border-t border-gray-100 flex justify-end">
                <button
                  onClick={() => setEditingRule(r)}
                  data-testid={`edit-rule-${r.rule_id}`}
                  className="text-xs font-bold text-[#001255] hover:underline flex items-center gap-1"
                >
                  <span className="material-symbols-outlined text-sm">edit</span>
                  <span>Configure Rule</span>
                </button>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Admin Edit Rule Modal */}
      {editingRule && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-gray-100 space-y-4 text-xs">
            <div className="flex items-center justify-between border-b border-gray-200 pb-3">
              <h3 className="text-sm font-bold text-[#001255]">Edit Rule: {editingRule.section}</h3>
              <button onClick={() => setEditingRule(null)} className="text-gray-400 hover:text-gray-600">
                <span className="material-symbols-outlined text-lg">close</span>
              </button>
            </div>

            <div>
              <label className="font-bold text-gray-700 block mb-1">Rule Title</label>
              <input
                type="text"
                data-testid="edit-rule-name-input"
                value={editingRule.rule_name}
                onChange={(e) => setEditingRule({ ...editingRule, rule_name: e.target.value })}
                className="w-full bg-gray-50 border border-gray-200 rounded-lg p-2"
              />
            </div>

            <div>
              <label className="font-bold text-gray-700 block mb-1">Statutory Description</label>
              <textarea
                rows={3}
                data-testid="edit-rule-desc-input"
                value={editingRule.description}
                onChange={(e) => setEditingRule({ ...editingRule, description: e.target.value })}
                className="w-full bg-gray-50 border border-gray-200 rounded-lg p-2"
              />
            </div>

            <div>
              <label className="font-bold text-gray-700 block mb-1">Severity Classification</label>
              <select
                data-testid="edit-rule-severity-select"
                value={editingRule.severity}
                onChange={(e) => setEditingRule({ ...editingRule, severity: e.target.value })}
                className="w-full bg-gray-50 border border-gray-200 rounded-lg p-2"
              >
                <option value="Critical">Critical</option>
                <option value="Major">Major</option>
                <option value="Minor">Minor</option>
              </select>
            </div>

            <div>
              <label className="font-bold text-gray-700 block mb-1">Penalty / Enforcement Clause</label>
              <input
                type="text"
                data-testid="edit-rule-penalty-input"
                value={editingRule.penalty_clause}
                onChange={(e) => setEditingRule({ ...editingRule, penalty_clause: e.target.value })}
                className="w-full bg-gray-50 border border-gray-200 rounded-lg p-2"
              />
            </div>

            <div className="flex justify-end gap-2 pt-3 border-t border-gray-200">
              <button
                onClick={() => setEditingRule(null)}
                className="px-3 py-1.5 rounded-lg text-gray-600 hover:bg-gray-100"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveRuleUpdate}
                data-testid="save-rule-update-btn"
                className="px-4 py-1.5 bg-[#001255] text-white font-bold rounded-lg"
              >
                Save Rule Settings
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}