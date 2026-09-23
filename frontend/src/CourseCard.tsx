import "./CourseCard.css";

interface CourseCardProps {
  course: any;
  onSelect: (course: any) => void;
}

function truncate(text: string, length: number) {
  return text.length > length ? `${text.substring(0, length).trimEnd()}...` : text;
}

export function CourseCard({ course, onSelect }: CourseCardProps) {
  const title = course.title || "Unknown Course";
  const number = course.number || "TBD";
  const faculty = course.faculty || "Staff";
  const time = course.time || "Time TBD";
  const category = course.category || "General";
  const description = course.description || "No description available";
  const credits = course.credits || "N/A";
  const room = (course.room || "").trim();

  return (
    <div
      className="course-card"
      role="button"
      tabIndex={0}
      aria-label={`View details for ${title}`}
      onClick={() => onSelect(course)}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onSelect(course);
        }
      }}
    >
      <div className="course-header">
        <div className="course-title-group">
          <h3 className="course-title">{title}</h3>
          <span className="course-number">{number}</span>
        </div>
      </div>

      <div className="course-faculty">{faculty}</div>

      <div className="course-meta">
        <span className="badge category">{category}</span>
        {credits && credits !== "N/A" && (
          <span className="badge credits">{credits} units</span>
        )}
      </div>

      <div className="course-timing">
        <p className="timing-item">
          <span className="timing-label">📅</span> {time}
        </p>
        {room && (
          <p className="timing-item">
            <span className="timing-label">📍</span> {room}
          </p>
        )}
      </div>

      <p className="course-description">{truncate(description, 280)}</p>

      {course.faculty_bio && (
        <div className="course-bio">
          <p className="bio-label">Faculty:</p>
          <p className="bio-text">{truncate(course.faculty_bio, 200)}</p>
        </div>
      )}

      <p className="view-details">View details →</p>
    </div>
  );
}
