 const todoForm = document.getElementById('todo-form');
const taskInput = document.getElementById('task-input');
const taskDateInput = document.getElementById('task-date');
const taskTimeInput = document.getElementById('task-time');
const todoList = document.getElementById('task-list');
const taskCount = document.getElementById('task-count');
const clearCompletedBtn = document.getElementById('clear-completed');

let tasks = [];

function getTodayDate() {
  return new Date().toISOString().slice(0, 10);
}

async function loadTasks() {
  try {
    const response = await fetch('/api/tasks');
    if (!response.ok) {
      throw new Error('Failed to load tasks');
    }
    tasks = await response.json();
    renderTasks();
  } catch (error) {
    console.error(error);
    todoList.innerHTML = '<div class="empty-state">Unable to load tasks right now.</div>';
  }
}

async function saveTasks() {
  // Intentionally left blank; server handles persistence.
}

function formatDate(dateValue) {
  if (!dateValue) {
    return 'No date';
  }

  const date = new Date(`${dateValue}T00:00:00`);
  return date.toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

function formatTime(timeValue) {
  if (!timeValue) {
    return 'Any time';
  }

  const [hours, minutes] = timeValue.split(':');
  const numericHours = Number(hours);
  const suffix = numericHours >= 12 ? 'PM' : 'AM';
  const formattedHour = ((numericHours + 11) % 12) + 1;
  return `${formattedHour}:${minutes} ${suffix}`;
}

function updateTaskCount() {
  const remainingTasks = tasks.filter((task) => !task.completed).length;
  const label = remainingTasks === 1 ? 'task' : 'tasks';
  taskCount.textContent = `${remainingTasks} ${label} remaining`;
}

function renderTasks() {
  todoList.innerHTML = '';

  if (tasks.length === 0) {
    const emptyState = document.createElement('div');
    emptyState.className = 'empty-state';
    emptyState.textContent = 'No tasks yet. Add one to get started!';
    todoList.appendChild(emptyState);
    updateTaskCount();
    return;
  }

  tasks.forEach((task) => {
    const item = document.createElement('div');
    item.className = `task-item ${task.completed ? 'completed-task' : ''}`;
    item.dataset.id = task.id;

    const mainContent = document.createElement('div');
    mainContent.className = 'task-main';

    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.checked = task.completed;
    checkbox.className = 'task-checkbox';
    checkbox.setAttribute('aria-label', `Mark task ${task.text} as complete`);
    checkbox.addEventListener('change', () => toggleTask(task.id));

    const content = document.createElement('div');
    content.className = 'task-content';

    const text = document.createElement('span');
    text.className = 'task-text';
    text.textContent = task.text;

    const meta = document.createElement('div');
    meta.className = 'task-meta';

    const dateMeta = document.createElement('span');
    dateMeta.textContent = `📅 ${formatDate(task.date)}`;

    const timeMeta = document.createElement('span');
    timeMeta.textContent = `⏰ ${formatTime(task.time)}`;

    const statusMeta = document.createElement('span');
    statusMeta.className = 'task-status';
    statusMeta.textContent = task.completed ? 'Completed' : 'Pending';

    meta.appendChild(dateMeta);
    meta.appendChild(timeMeta);
    meta.appendChild(statusMeta);

    content.appendChild(text);
    content.appendChild(meta);

    mainContent.appendChild(checkbox);
    mainContent.appendChild(content);

    const actions = document.createElement('div');
    actions.className = 'task-actions';

    const editButton = document.createElement('button');
    editButton.type = 'button';
    editButton.className = 'btn btn-sm btn-outline-primary task-action';
    editButton.textContent = 'Edit';
    editButton.addEventListener('click', () => editTask(task.id));

    const deleteButton = document.createElement('button');
    deleteButton.type = 'button';
    deleteButton.className = 'btn btn-sm btn-outline-danger task-action';
    deleteButton.textContent = 'Delete';
    deleteButton.addEventListener('click', () => deleteTask(task.id));

    actions.appendChild(editButton);
    actions.appendChild(deleteButton);

    item.appendChild(mainContent);
    item.appendChild(actions);
    todoList.appendChild(item);
  });

  updateTaskCount();
}

async function addTask() {
  const text = taskInput.value.trim();

  if (!text) {
    taskInput.focus();
    return;
  }

  try {
    const response = await fetch('/api/tasks', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        text,
        date: taskDateInput.value || getTodayDate(),
        time: taskTimeInput.value || '09:00',
      }),
    });

    if (!response.ok) {
      throw new Error('Could not add task');
    }

    taskInput.value = '';
    taskDateInput.value = getTodayDate();
    taskTimeInput.value = '09:00';
    taskInput.focus();
    await loadTasks();
  } catch (error) {
    console.error(error);
  }
}

async function toggleTask(taskId) {
  const task = tasks.find((item) => item.id === taskId);
  if (!task) {
    return;
  }

  try {
    const response = await fetch(`/api/tasks/${taskId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        text: task.text,
        date: task.date,
        time: task.time,
        completed: !task.completed,
      }),
    });

    if (!response.ok) {
      throw new Error('Could not toggle task');
    }

    await loadTasks();
  } catch (error) {
    console.error(error);
  }
}

function editTask(taskId) {
  const task = tasks.find((item) => item.id === taskId);

  if (!task) {
    return;
  }

  const updatedText = window.prompt('Edit task:', task.text);

  if (updatedText === null) {
    return;
  }

  const trimmedText = updatedText.trim();

  if (!trimmedText) {
    return;
  }

  const updateTaskRequest = async () => {
    try {
      const response = await fetch(`/api/tasks/${taskId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          text: trimmedText,
          date: task.date,
          time: task.time,
          completed: task.completed,
        }),
      });

      if (!response.ok) {
        throw new Error('Could not edit task');
      }

      await loadTasks();
    } catch (error) {
      console.error(error);
    }
  };

  updateTaskRequest();
}

async function deleteTask(taskId) {
  try {
    const response = await fetch(`/api/tasks/${taskId}`, {
      method: 'DELETE',
    });

    if (!response.ok) {
      throw new Error('Could not delete task');
    }

    await loadTasks();
  } catch (error) {
    console.error(error);
  }
}

async function clearCompleted() {
  try {
    const response = await fetch('/api/tasks/clear-completed', {
      method: 'DELETE',
    });

    if (!response.ok) {
      throw new Error('Could not clear completed tasks');
    }

    await loadTasks();
  } catch (error) {
    console.error(error);
  }
}

const today = getTodayDate();
taskDateInput.value = today;
taskTimeInput.value = '09:00';

todoForm.addEventListener('submit', (event) => {
  event.preventDefault();
  addTask();
});

taskInput.addEventListener('keydown', (event) => {
  if (event.key === 'Enter') {
    event.preventDefault();
    addTask();
  }
});

clearCompletedBtn.addEventListener('click', clearCompleted);

loadTasks();
