document.addEventListener("DOMContentLoaded", () => {
  const activitiesList = document.getElementById("activities-list");
  const activitySelect = document.getElementById("activity");
  const signupForm = document.getElementById("signup-form");
  const teacherRequired = document.getElementById("teacher-required");
  const messageDiv = document.getElementById("message");
  const teacherMenuToggle = document.getElementById("teacher-menu-toggle");
  const teacherMenu = document.getElementById("teacher-menu");
  const teacherStatus = document.getElementById("teacher-status");
  const loginButton = document.getElementById("teacher-login-button");
  const logoutButton = document.getElementById("teacher-logout-button");
  const loginDialog = document.getElementById("teacher-login-dialog");
  const loginForm = document.getElementById("teacher-login-form");
  const loginError = document.getElementById("teacher-login-error");
  let teacherUsername = null;
  let messageTimeout;

  function showMessage(message, type) {
    messageDiv.textContent = message;
    messageDiv.className = `message ${type}`;
    clearTimeout(messageTimeout);
    messageTimeout = setTimeout(() => messageDiv.classList.add("hidden"), 5000);
  }

  async function responseMessage(response) {
    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.detail || "An error occurred");
    }
    return result;
  }

  function setTeacherState(username) {
    teacherUsername = username;
    const isTeacher = Boolean(username);
    signupForm.hidden = !isTeacher;
    teacherRequired.hidden = isTeacher;
    teacherStatus.hidden = !isTeacher;
    teacherStatus.textContent = isTeacher ? `Signed in as ${username}` : "";
    loginButton.hidden = isTeacher;
    logoutButton.hidden = !isTeacher;
  }

  async function refreshTeacherSession() {
    const response = await fetch("/teachers/session");
    const session = await responseMessage(response);
    setTeacherState(session.authenticated ? session.username : null);
  }

  function createElement(tag, className, text) {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (text !== undefined) element.textContent = text;
    return element;
  }

  function renderActivities(activities) {
    activitiesList.replaceChildren();
    activitySelect.replaceChildren(new Option("-- Select an activity --", ""));

    Object.entries(activities).forEach(([name, details]) => {
      const activityCard = createElement("div", "activity-card");
      activityCard.appendChild(createElement("h4", "", name));
      activityCard.appendChild(createElement("p", "", details.description));
      const schedule = createElement("p");
      schedule.appendChild(createElement("strong", "", "Schedule: "));
      schedule.append(document.createTextNode(details.schedule));
      activityCard.appendChild(schedule);

      const spotsLeft = details.max_participants - details.participants.length;
      const availability = createElement("p");
      availability.appendChild(createElement("strong", "", "Availability: "));
      availability.append(document.createTextNode(`${spotsLeft} spots left`));
      activityCard.appendChild(availability);

      const participantsContainer = createElement("div", "participants-container");
      if (details.participants.length > 0) {
        const participantSection = createElement("div", "participants-section");
        participantSection.appendChild(createElement("h5", "", "Participants:"));
        const participantsList = createElement("ul", "participants-list");

        details.participants.forEach((email) => {
          const item = createElement("li");
          item.appendChild(createElement("span", "participant-email", email));
          if (teacherUsername) {
            const deleteButton = createElement("button", "delete-btn", "Remove");
            deleteButton.type = "button";
            deleteButton.dataset.activity = name;
            deleteButton.dataset.email = email;
            deleteButton.setAttribute("aria-label", `Remove ${email} from ${name}`);
            item.appendChild(deleteButton);
          }
          participantsList.appendChild(item);
        });

        participantSection.appendChild(participantsList);
        participantsContainer.appendChild(participantSection);
      } else {
        participantsContainer.appendChild(
          createElement("p", "", "No participants yet")
        );
      }

      activityCard.appendChild(participantsContainer);
      activitiesList.appendChild(activityCard);

      activitySelect.appendChild(new Option(name, name));
    });
  }

  async function fetchActivities() {
    try {
      const response = await fetch("/activities");
      const activities = await responseMessage(response);
      renderActivities(activities);
    } catch (error) {
      activitiesList.replaceChildren(
        createElement("p", "", "Failed to load activities. Please try again.")
      );
      console.error("Error fetching activities:", error);
    }
  }

  async function updateParticipant(activity, email, method) {
    try {
      const url = `/activities/${encodeURIComponent(activity)}/${method}?email=${encodeURIComponent(email)}`;
      const response = await fetch(url, { method: method === "signup" ? "POST" : "DELETE" });
      const result = await responseMessage(response);
      showMessage(result.message, "success");
      await fetchActivities();
      return true;
    } catch (error) {
      showMessage(error.message || "Unable to update the activity.", "error");
      console.error("Error updating activity registration:", error);
      return false;
    }
  }

  activitiesList.addEventListener("click", (event) => {
    const button = event.target.closest(".delete-btn");
    if (button) {
      updateParticipant(button.dataset.activity, button.dataset.email, "unregister");
    }
  });

  signupForm.addEventListener("submit", (event) => {
    event.preventDefault();
    const email = document.getElementById("email").value;
    const activity = activitySelect.value;
    updateParticipant(activity, email, "signup").then((succeeded) => {
      if (succeeded) signupForm.reset();
    });
  });

  teacherMenuToggle.addEventListener("click", () => {
    teacherMenu.hidden = !teacherMenu.hidden;
    teacherMenuToggle.setAttribute("aria-expanded", String(!teacherMenu.hidden));
  });

  loginButton.addEventListener("click", () => {
    teacherMenu.hidden = true;
    teacherMenuToggle.setAttribute("aria-expanded", "false");
    loginError.hidden = true;
    loginDialog.showModal();
  });

  document.getElementById("teacher-login-cancel").addEventListener("click", () => {
    loginDialog.close();
  });

  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    loginError.hidden = true;
    const credentials = {
      username: document.getElementById("teacher-username").value,
      password: document.getElementById("teacher-password").value,
    };

    try {
      const response = await fetch("/teachers/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(credentials),
      });
      const result = await responseMessage(response);
      loginForm.reset();
      loginDialog.close();
      setTeacherState(result.username);
      showMessage(`Signed in as ${result.username}`, "success");
      await fetchActivities();
    } catch (error) {
      loginError.textContent = error.message || "Unable to sign in.";
      loginError.hidden = false;
    }
  });

  logoutButton.addEventListener("click", async () => {
    try {
      const response = await fetch("/teachers/logout", { method: "POST" });
      await responseMessage(response);
      setTeacherState(null);
      teacherMenu.hidden = true;
      teacherMenuToggle.setAttribute("aria-expanded", "false");
      await fetchActivities();
      showMessage("You have been signed out.", "success");
    } catch (error) {
      showMessage(error.message || "Unable to sign out.", "error");
      console.error("Error signing out:", error);
    }
  });

  async function initialize() {
    try {
      await refreshTeacherSession();
    } catch (error) {
      setTeacherState(null);
      console.error("Error loading teacher session:", error);
    }
    await fetchActivities();
  }

  initialize();
});
