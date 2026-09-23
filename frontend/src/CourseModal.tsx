import { useEffect } from "react";
import "./CourseModal.css";

interface CourseModalProps {
  course: any;
  onClose: () => void;
}

const SESSION_LABELS: Record<string, string> = {
  "fall-1": "Fall 1",
  "fall-2": "Fall 2",
  fall: "Full Fall semester",
};

const ENROLLMENT_LABELS: Record<string, string> = {
  bid: "Bidding",
  permission: "Instructor permission",
  core: "Core",
  PHD: "PhD",
  EMBA: "EMBA",
};

function formatDate(iso: string) {
  if (!iso) return "";
  const [year, month, day] = iso.split("-").map(Number);
  return new Date(year, month - 1, day).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  });
}

// The source text is hard-wrapped mid-sentence; rebuild real paragraphs
function toParagraphs(text: string) {
  return text
    .split(/\r?\n\s*\r?\n/)
    .map((p) => p.replace(/\s*\r?\n\s*/g, " ").trim())
    .filter(Boolean);
}

// Bios end with a markdown link like "([som.yale.edu](https://...))"
function splitBio(bio: string) {
  const match = bio.match(/\s*\(\[([^\]]+)\]\((https?:[^)]+)\)\)\s*$/);
  if (!match) return { text: bio, link: "" };
  return { text: bio.slice(0, match.index), link: match[2] };
}

export function CourseModal({ course, onClose }: CourseModalProps) {
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [onClose]);

  const session = SESSION_LABELS[course.session] || course.session || "TBD";
  const dates =
    course.start_date && course.end_date
      ? `${formatDate(course.start_date)} – ${formatDate(course.end_date)}`
      : "";
  const enrollment = ENROLLMENT_LABELS[course.enrollment] || course.enrollment;
  const bio = splitBio(course.faculty_bio || "");

  const details = [
    { label: "Faculty", value: course.faculty || "Staff" },
    { label: "Session", value: dates ? `${session} (${dates})` : session },
    { label: "Schedule", value: course.time || "Time TBD" },
    { label: "Room", value: (course.room || "").trim() },
    { label: "Category", value: course.category },
    { label: "Units", value: course.credits },
    { label: "Enrollment", value: enrollment },
  ].filter((d) => d.value);

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
        onClick={(e) => e.stopPropagation()}
      >
        <button className="modal-close" onClick={onClose} aria-label="Close">
          ×
        </button>

        <span className="modal-number">{course.number}</span>
        <h2 id="modal-title" className="modal-title">
          {course.title}
        </h2>

        <dl className="modal-details">
          {details.map((d) => (
            <div key={d.label} className="modal-detail">
              <dt>{d.label}</dt>
              <dd>{d.value}</dd>
            </div>
          ))}
        </dl>

        {course.description && (
          <section className="modal-section">
            <h3>Description</h3>
            {toParagraphs(course.description).map((p, i) => (
              <p key={i}>{p}</p>
            ))}
          </section>
        )}

        {bio.text && (
          <section className="modal-section">
            <h3>About the faculty</h3>
            <p>{bio.text}</p>
          </section>
        )}

        <div className="modal-links">
          {course.syllabus && (
            <a href={course.syllabus} target="_blank" rel="noreferrer">
              Syllabus ↗
            </a>
          )}
          {bio.link && (
            <a href={bio.link} target="_blank" rel="noreferrer">
              Faculty profile ↗
            </a>
          )}
          {course.faculty_email && (
            <a href={`mailto:${course.faculty_email}`}>Email faculty</a>
          )}
        </div>
      </div>
    </div>
  );
}
