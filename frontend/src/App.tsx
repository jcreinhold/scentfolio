import { lazy, Suspense } from "react";
import { BrowserRouter, Routes, Route, NavLink } from "react-router-dom";
import Collection from "./views/Collection";
import PerfumeDetail from "./views/PerfumeDetail";
import Add from "./views/Add";
import Glossary from "./views/Glossary";
import NoteDetail from "./views/NoteDetail";
import "./styles.css";

const Insights = lazy(() => import("./views/Insights"));

export default function App() {
  return (
    <BrowserRouter>
      <div className="layout">
        <div className="sidebar">
          <div className="brand">Scentfolio</div>
          <div className="brand-eyebrow">Personal Fragrance Archive</div>
          <nav>
            <NavLink to="/" end>
              Collection
            </NavLink>
            <NavLink to="/saved">Saved</NavLink>
            <NavLink to="/add">Add a Scent</NavLink>
            <NavLink to="/insights">Insights</NavLink>
            <NavLink to="/glossary">Note Glossary</NavLink>
          </nav>
          <div className="sidebar-foot">Est. in your vanity</div>
        </div>
        <main className="content">
          <Routes>
            <Route
              path="/"
              element={<Collection key="collection" status="collection" />}
            />
            <Route
              path="/saved"
              element={<Collection key="saved" status="saved" />}
            />
            <Route path="/add" element={<Add />} />
            <Route path="/perfume/:id" element={<PerfumeDetail />} />
            <Route
              path="/insights"
              element={
                <Suspense fallback={<div role="status">Loading insights…</div>}>
                  <Insights />
                </Suspense>
              }
            />
            <Route path="/glossary" element={<Glossary />} />
            <Route path="/note/:name" element={<NoteDetail />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
