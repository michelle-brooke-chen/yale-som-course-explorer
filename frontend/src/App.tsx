import { useState, useEffect, useCallback } from "react";
import { clearToken, getCourses, getCurrentUser, onUnauthorized } from "./api";
import type { User } from "./api";
import { AuthScreen } from "./AuthScreen";
import { CourseCard } from "./CourseCard";
import { CourseModal } from "./CourseModal";
import { ChatPanel } from "./ChatPanel";
import "./App.css";

function App() {
  const [user, setUser] = useState<User | null>(null);
  const [checkingSession, setCheckingSession] = useState(true);

  useEffect(() => {
    onUnauthorized(() => setUser(null));
    getCurrentUser()
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setCheckingSession(false));
  }, []);

  const signOut = () => {
    clearToken();
    setUser(null);
  };

  if (checkingSession) {
    return <div className="loading">Loading...</div>;
  }

  if (!user) {
    return <AuthScreen onAuthenticated={setUser} />;
  }

  return <CourseExplorer user={user} onSignOut={signOut} />;
}

interface CourseExplorerProps {
  user: User;
  onSignOut: () => void;
}

function CourseExplorer({ user, onSignOut }: CourseExplorerProps) {
  const [courses, setCourses] = useState<any[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [filteredCourses, setFilteredCourses] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedCourse, setSelectedCourse] = useState<any | null>(null);
  const closeModal = useCallback(() => setSelectedCourse(null), []);

  useEffect(() => {
    const loadCourses = async () => {
      try {
        setLoading(true);
        const data = await getCourses();
        setCourses(data.courses);
        setFilteredCourses(data.courses);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load courses");
      } finally {
        setLoading(false);
      }
    };

    loadCourses();
  }, []);

  const handleSearch = (query: string) => {
    setSearchQuery(query);
    if (!query.trim()) {
      setFilteredCourses(courses);
      return;
    }

    // Match every word in any order, so "Kai Hao Yang" finds "Yang, Kai Hao"
    const toWords = (text: string) =>
      text.toLowerCase().replace(/['’]s\b/g, "").match(/[a-z0-9]+/g) ?? [];
    const words = toWords(query);
    const filtered = courses.filter((course: any) => {
      const haystack = toWords(
        [course.title, course.number, course.faculty, course.description, course.category]
          .filter(Boolean)
          .join(" ")
      ).join(" ");
      return words.every((word) => haystack.includes(word));
    });

    setFilteredCourses(filtered);
  };

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-content">
          <div className="header-text">
            <h1>Yale SOM Course Explorer</h1>
            <p>Fall 2026 Courses • Discover and explore Yale School of Management offerings</p>
          </div>
          <div className="header-user">
            <span className="header-username">Signed in as {user.username}</span>
            <button className="sign-out" onClick={onSignOut}>
              Sign out
            </button>
          </div>
        </div>
      </header>

      <div className="app-layout">
        <main className="main-content">
          <div className="search-section">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => handleSearch(e.target.value)}
              placeholder="Search by course title, number, faculty, or category..."
              className="search-input"
              disabled={loading}
            />
          </div>

          {error && <div className="error-message">{error}</div>}

          <div className="courses-section">
            <div className="courses-header">
              <h2>Courses ({filteredCourses.length})</h2>
              {searchQuery && (
                <button
                  className="clear-search"
                  onClick={() => {
                    setSearchQuery("");
                    setFilteredCourses(courses);
                  }}
                >
                  Clear Search
                </button>
              )}
            </div>

            {loading ? (
              <div className="loading">Loading Yale SOM courses...</div>
            ) : filteredCourses.length === 0 ? (
              <div className="empty-state">
                <p>
                  {searchQuery
                    ? "No courses found. Try a different search term."
                    : "No courses available."}
                </p>
              </div>
            ) : (
              <div className="courses-grid">
                {filteredCourses.map((course: any) => (
                  <CourseCard
                    key={course.id}
                    course={course}
                    onSelect={setSelectedCourse}
                  />
                ))}
              </div>
            )}
          </div>
        </main>

        <aside className="sidebar">
          <ChatPanel key={user.id} />
        </aside>
      </div>

      {selectedCourse && (
        <CourseModal course={selectedCourse} onClose={closeModal} />
      )}
    </div>
  );
}

export default App;
