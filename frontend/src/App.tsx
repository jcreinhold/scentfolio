import { BrowserRouter, Routes, Route, NavLink } from "react-router-dom";
import Collection from "./views/Collection";
import PerfumeDetail from "./views/PerfumeDetail";
import Add from "./views/Add";
import Glossary from "./views/Glossary";
import NoteDetail from "./views/NoteDetail";
import Insights from "./views/Insights";
import "./styles.css";

export default function App() {
  return (
    <BrowserRouter>
      <div className="layout">
        <div className="sidebar">
          <div className="brand">Scentfolio</div>
          <div className="brand-eyebrow">Personal Fragrance Archive</div>
          <nav>
            <NavLink to="/" end>Collection</NavLink>
            <NavLink to="/add">Add a Scent</NavLink>
            <NavLink to="/insights">Insights</NavLink>
            <NavLink to="/glossary">Note Glossary</NavLink>
          </nav>
          <div className="sidebar-foot">Est. in your vanity</div>
        </div>
        <main className="content">
          <Routes>
            <Route path="/" element={<Collection />} />
            <Route path="/add" element={<Add />} />
            <Route path="/perfume/:id" element={<PerfumeDetail />} />
            <Route path="/insights" element={<Insights />} />
            <Route path="/glossary" element={<Glossary />} />
            <Route path="/note/:name" element={<NoteDetail />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
