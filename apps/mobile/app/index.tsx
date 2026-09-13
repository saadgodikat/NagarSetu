import { Redirect } from 'expo-router'

export default function Index() {
  const [email, setEmail] = useState("amit@demo.solapur");
  const [password, setPassword] = useState("Demo@1234");
  const [isLoading, setIsLoading] = useState(false);
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<UserSummary | null>(null);
  const [message, setMessage] = useState("Citizen / worker login (L1)");
  const [title, setTitle] = useState("Garbage not collected for 4 days");
  const [description, setDescription] = useState(
    "Garbage has not been collected for 4 days near Tuljapur Naka. It is unsafe.",
  );
  const [latitude, setLatitude] = useState("17.6599");
  const [longitude, setLongitude] = useState("75.9064");
  const [selectedPhoto, setSelectedPhoto] = useState<ImagePicker.ImagePickerAsset | null>(null);
  const [aiPrediction, setAiPrediction] = useState<AiClassifyResult | null>(null);
  const [classifying, setClassifying] = useState(false);
  const [categoryOverride, setCategoryOverride] = useState<string | null>(null);
  const [complaints, setComplaints] = useState<ComplaintSummary[]>([]);
  const [rejectingComplaintId, setRejectingComplaintId] = useState<string | null>(null);
  const [rejectionReason, setRejectionReason] = useState("");
  const [workerTasks, setWorkerTasks] = useState<ComplaintSummary[]>([]);
  const [selectedTask, setSelectedTask] = useState<ComplaintSummary | null>(null);
  const [workerNote, setWorkerNote] = useState("");
  const [supportDescription, setSupportDescription] = useState("");
  const [resolutionPhoto, setResolutionPhoto] = useState<ImagePicker.ImagePickerAsset | null>(null);
  const [workerSubmitting, setWorkerSubmitting] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  async function runAiClassification(photoAsset: ImagePicker.ImagePickerAsset, currentDescription: string) {
    if (!token) return;
    setClassifying(true);
    try {
      const formData = new FormData();
      const filename = photoAsset.uri.split("/").pop() ?? "photo.jpg";
      const ext = filename.split(".").pop()?.toLowerCase() ?? "jpg";
      const mimeType = ext === "png" ? "image/png" : "image/jpeg";
      // @ts-ignore - React Native FormData accepts this shape
      formData.append("photo", { uri: photoAsset.uri, name: filename, type: mimeType });
      if (currentDescription.trim()) {
        formData.append("description", currentDescription.trim());
      }
      const classifyResult = await api<AiClassifyResult>(
        "/api/v1/ai/classify",
        token,
        {
          method: "POST",
          body: formData,
        },
      );
      setAiPrediction(classifyResult);
      setCategoryOverride(classifyResult.category);
      setMessage(`AI detected: ${classifyResult.category} (${Math.round(classifyResult.confidence * 100)}% via ${classifyResult.source})`);
    } catch (err) {
      console.warn("AI Classification preview failed:", err);
    } finally {
      setClassifying(false);
    }
  }

  const fetchComplaints = async (authToken: string) => {
    const data = await api<{ data: ComplaintSummary[]; pagination: { totalItems: number } }>(
      "/api/v1/complaints",
      authToken,
    );
    setComplaints(data.data ?? []);
  };

  const fetchWorkerTasks = async (authToken: string) => {
    const data = await api<{ data: ComplaintSummary[] }>(
      "/api/v1/worker/complaints",
      authToken,
    );
    setWorkerTasks(data.data ?? []);
  };

  useEffect(() => {
    if (!token) {
      setUser(null);
      return;
    }

    const bootstrap = async () => {
      try {
        const me = await api<UserSummary>("/api/v1/auth/me", token);
        setUser(me);
        if (me.role === "field_worker") {
          await fetchWorkerTasks(token);
        } else if (me.role === "citizen") {
          await fetchComplaints(token);
        }
      } catch (error) {
        setMessage(error instanceof Error ? error.message : "Session expired");
        setToken(null);
      }
    };

    void bootstrap();
  }, [token]);

  async function login() {
    setIsLoading(true);
    setMessage("Signing in...");
    try {
      const loginData = await api<{ access_token: string }>(
        "/api/v1/auth/login",
        undefined,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email, password }),
        },
      );
      setToken(loginData.access_token);
      const me = await api<UserSummary>("/api/v1/auth/me", loginData.access_token);
      setUser(me);
      setMessage(`${me.role}: ${me.name}`);
      if (me.role === "field_worker") {
        await fetchWorkerTasks(loginData.access_token);
      } else if (me.role === "citizen") {
        await fetchComplaints(loginData.access_token);
      }
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Login failed");
    } finally {
      setIsLoading(false);
    }
  }

  async function useCurrentLocation() {
    try {
      const { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== "granted") {
        Alert.alert("Location permission denied", "Allow access to capture GPS for the complaint.");
        return;
      }
      const current = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Low });
      setLatitude(String(current.coords.latitude));
      setLongitude(String(current.coords.longitude));
      setMessage("Current GPS captured");
    } catch (error) {
      Alert.alert(
        "Location unavailable",
        error instanceof Error ? error.message : "Unable to get current location.",
      );
    }
  }

  async function pickPhoto() {
    try {
      const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();
      if (status !== "granted") {
        Alert.alert("Photo permission denied", "Allow access to choose a complaint image before submission.");
        return;
      }
      const result = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ["images"],
        allowsEditing: true,
        quality: 0.8,
      });
      if (!result.canceled && result.assets.length > 0) {
        const asset = result.assets[0];
        setSelectedPhoto(asset);
        void runAiClassification(asset, description);
      }
    } catch (error) {
      Alert.alert(
        "Image selection failed",
        error instanceof Error ? error.message : "Unable to pick an image.",
      );
    }
  }

  async function pickResolutionPhoto() {
    try {
      const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();
      if (status !== "granted") {
        Alert.alert("Photo permission denied", "Allow access to choose resolution evidence.");
        return;
      }
      const result = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ["images"],
        allowsEditing: true,
        quality: 0.8,
      });
      if (!result.canceled && result.assets.length > 0) {
        setResolutionPhoto(result.assets[0]);
      }
    } catch (error) {
      Alert.alert(
        "Image selection failed",
        error instanceof Error ? error.message : "Unable to pick a resolution image.",
      );
    }
  }

  async function openWorkerTask(taskId: string) {
    if (!token) return;
    try {
      const detail = await api<ComplaintSummary>(`/api/v1/worker/complaints/${taskId}`, token);
      setSelectedTask(detail);
      setMessage("Task details loaded");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to load task");
    }
  }

  async function updateWorkerStatus(status: "in_progress" | "resolution_submitted") {
    if (!token || !selectedTask) return;
    setWorkerSubmitting(true);
    try {
      const updated = await api<ComplaintSummary>(
        `/api/v1/worker/complaints/${selectedTask.id}/status?status=${status}`,
        token,
        { method: "PATCH" },
      );
      setSelectedTask(updated);
      await fetchWorkerTasks(token);
      setMessage(`Task status updated to ${status}`);
    } catch (error) {
      Alert.alert("Status update failed", error instanceof Error ? error.message : "Unable to update task");
    } finally {
      setWorkerSubmitting(false);
    }
  }

  async function addWorkerNote() {
    if (!token || !selectedTask || !workerNote.trim()) return;
    setWorkerSubmitting(true);
    try {
      const updated = await api<ComplaintSummary>(
        `/api/v1/worker/complaints/${selectedTask.id}/notes`,
        token,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ note: workerNote.trim() }),
        },
      );
      setSelectedTask(updated);
      setWorkerNote("");
      setMessage("Worker note added");
    } catch (error) {
      Alert.alert("Note failed", error instanceof Error ? error.message : "Unable to add note");
    } finally {
      setWorkerSubmitting(false);
    }
  }

  async function requestSupport() {
    if (!token || !selectedTask || !supportDescription.trim()) return;
    setWorkerSubmitting(true);
    try {
      const updated = await api<ComplaintSummary>(
        `/api/v1/worker/complaints/${selectedTask.id}/support-requests`,
        token,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ description: supportDescription.trim() }),
        },
      );
      setSelectedTask(updated);
      setSupportDescription("");
      setMessage("Support request sent");
    } catch (error) {
      Alert.alert("Support request failed", error instanceof Error ? error.message : "Unable to request support");
    } finally {
      setWorkerSubmitting(false);
    }
  }

  async function uploadResolutionPhoto() {
    if (!token || !selectedTask || !resolutionPhoto) {
      Alert.alert("Photo required", "Choose a resolution photo first.");
      return;
    }
    setWorkerSubmitting(true);
    try {
      const formData = new FormData();
      const resFilename = resolutionPhoto.uri.split("/").pop() ?? "photo.jpg";
      const resExt = resFilename.split(".").pop()?.toLowerCase() ?? "jpg";
      const resMime = resExt === "png" ? "image/png" : "image/jpeg";
      // @ts-ignore - React Native FormData accepts this shape
      formData.append("photo", { uri: resolutionPhoto.uri, name: resFilename, type: resMime });
      const updated = await api<ComplaintSummary>(
        `/api/v1/worker/complaints/${selectedTask.id}/resolution-photo`,
        token,
        { method: "POST", body: formData },
      );
      setSelectedTask(updated);
      setResolutionPhoto(null);
      await fetchWorkerTasks(token);
      setMessage("Resolution photo uploaded");
    } catch (error) {
      Alert.alert("Upload failed", error instanceof Error ? error.message : "Unable to upload resolution photo");
    } finally {
      setWorkerSubmitting(false);
    }
  }

  async function confirmResolution(complaintId: string) {
    if (!token) return;
    try {
      const updated = await api<ComplaintSummary>(
        `/api/v1/complaints/${complaintId}/resolution/confirm`,
        token,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({}),
        },
      );
      setComplaints((current) => current.map((item) => item.id === updated.id ? updated : item));
      setMessage("Resolution confirmed; complaint closed");
    } catch (error) {
      Alert.alert("Confirmation failed", error instanceof Error ? error.message : "Unable to confirm resolution");
    }
  }

  async function rejectResolution(complaintId: string) {
    if (!token) return;
    if (!rejectionReason.trim()) {
      Alert.alert("Reason required", "Explain what still needs to be fixed.");
      return;
    }
    try {
      const updated = await api<ComplaintSummary>(
        `/api/v1/complaints/${complaintId}/resolution/reject`,
        token,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ reason: rejectionReason.trim() }),
        },
      );
      setComplaints((current) => current.map((item) => item.id === updated.id ? updated : item));
      setRejectingComplaintId(null);
      setRejectionReason("");
      setMessage("More work requested; complaint reopened");
    } catch (error) {
      Alert.alert("Rejection failed", error instanceof Error ? error.message : "Unable to reject resolution");
    }
  }

  async function submitComplaint() {
    if (!token) {
      Alert.alert("Sign in first", "Log in as a citizen before submitting a complaint.");
      return;
    }

    if (!title.trim() || !description.trim()) {
      Alert.alert("Missing details", "Add a title and description before submitting.");
      return;
    }
    if (!selectedPhoto) {
      Alert.alert("Photo required", "Attach a photo to continue.");
      return;
    }
    setSubmitting(true);
    try {
      const formData = new FormData();
      formData.append("title", title.trim());
      formData.append("description", description.trim());
      formData.append("latitude", latitude);
      formData.append("longitude", longitude);

      const filename = selectedPhoto.uri.split("/").pop() ?? "photo.jpg";
      const ext = filename.split(".").pop()?.toLowerCase() ?? "jpg";
      const mimeType = ext === "png" ? "image/png" : "image/jpeg";
      // @ts-ignore - React Native FormData accepts this shape
      formData.append("photo", { uri: selectedPhoto.uri, name: filename, type: mimeType });
      if (categoryOverride) {
        formData.append("category", categoryOverride);
      }

      const created = await api<{ id: string; title: string; status: string }>(
        "/api/v1/complaints",
        token,
        {
          method: "POST",
          body: formData,
        },
      );

      setTitle("");
      setDescription("");
      setSelectedPhoto(null);
      setAiPrediction(null);
      setCategoryOverride(null);
      setMessage(`Complaint ${created.id.slice(0, 8)} submitted (${created.status})`);
      await fetchComplaints(token);
    } catch (error) {
      Alert.alert("Submission failed", error instanceof Error ? error.message : "Unable to submit complaint.");
    } finally {
      setSubmitting(false);
    }
  }

  if (!token || !user) {
    return (
      <View style={styles.shell}>
        <Text style={styles.title}>NagarIQ</Text>
        <Text style={styles.subtitle}>Citizen complaint submission</Text>
        <TextInput
          autoCapitalize="none"
          value={email}
          onChangeText={setEmail}
          placeholder="Email"
          style={styles.input}
        />
        <TextInput
          secureTextEntry
          value={password}
          onChangeText={setPassword}
          placeholder="Password"
          style={styles.input}
        />
        <Pressable
          onPress={login}
          disabled={isLoading}
          style={[styles.primaryButton, isLoading && styles.disabledButton]}
        >
          {isLoading ? <ActivityIndicator color="#fff" /> : <Text style={styles.primaryButtonText}>Sign in</Text>}
        </Pressable>
        <Text style={styles.message}>{message}</Text>
      </View>
    );
  }

  if (user.role !== "citizen") {
    if (user.role === "field_worker") {
      return (
        <WorkerPortal
          user={user}
          tasks={workerTasks}
          selectedTask={selectedTask}
          workerNote={workerNote}
          supportDescription={supportDescription}
          resolutionPhoto={resolutionPhoto}
          submitting={workerSubmitting}
          message={message}
          onSignOut={() => setToken(null)}
          onRefresh={() => token && fetchWorkerTasks(token)}
          onOpenTask={openWorkerTask}
          onStatus={updateWorkerStatus}
          onNoteChange={setWorkerNote}
          onAddNote={addWorkerNote}
          onSupportChange={setSupportDescription}
          onRequestSupport={requestSupport}
          onPickPhoto={pickResolutionPhoto}
          onUploadPhoto={uploadResolutionPhoto}
        />
      );
    }
    return (
      <View style={styles.shell}>
        <Text style={styles.title}>NagarIQ</Text>
        <Text style={styles.subtitle}>Role switch</Text>
        <Text style={styles.card}>Signed in as {user.role}. This demo supports the citizen complaint flow of L1.</Text>
        <Pressable onPress={() => setToken(null)} style={styles.primaryButton}>
          <Text style={styles.primaryButtonText}>Sign out</Text>
        </Pressable>
      </View>
    );
  }

  return (
    <ScrollView contentContainerStyle={styles.scrollContent}>
      <View style={styles.headerRow}>
        <Text style={styles.title}>Citizen Portal</Text>
        <Pressable onPress={() => setToken(null)}>
          <Text style={styles.linkText}>Sign out</Text>
        </Pressable>
      </View>
      <Text style={styles.greeting}>Welcome, {user.name}</Text>

      <View style={styles.card}>
        <Text style={styles.sectionTitle}>Submit complaint</Text>
        <TextInput value={title} onChangeText={setTitle} placeholder="Title" style={styles.input} />
        <TextInput
          value={description}
          onChangeText={setDescription}
          placeholder="Describe the issue"
          multiline
          numberOfLines={5}
          style={[styles.input, styles.textArea]}
        />

        <View style={styles.fieldRow}>
          <TextInput
            value={latitude}
            onChangeText={setLatitude}
            placeholder="Latitude"
            keyboardType="decimal-pad"
            style={[styles.input, styles.inlineInput]}
          />
          <TextInput
            value={longitude}
            onChangeText={setLongitude}
            placeholder="Longitude"
            keyboardType="decimal-pad"
            style={[styles.input, styles.inlineInput]}
          />
        </View>

        <Pressable onPress={useCurrentLocation} style={styles.secondaryButton}>
          <Text style={styles.secondaryButtonText}>Use current GPS</Text>
        </Pressable>

        <Pressable onPress={pickPhoto} style={styles.secondaryButton}>
          <Text style={styles.secondaryButtonText}>Choose photo</Text>
        </Pressable>

        {selectedPhoto ? (
          <View style={styles.previewWrap}>
            <Image source={{ uri: selectedPhoto.uri }} style={styles.previewImage} />
            <Text style={styles.helperText}>{selectedPhoto.fileName ?? "Selected image"}</Text>
          </View>
        ) : null}

        {classifying ? (
          <View style={styles.aiLoadingCard}>
            <ActivityIndicator size="small" color="#1f4d3a" />
            <Text style={styles.aiLoadingText}>Running MobileNetV3 Vision AI analysis...</Text>
          </View>
        ) : aiPrediction ? (
          <View style={styles.aiPredictionCard}>
            <View style={styles.aiHeaderRow}>
              <Text style={styles.aiTag}>🤖 AI Vision Detection</Text>
              <Text style={styles.aiSourceBadge}>
                {aiPrediction.source === "vision_mobilenet_v3" ? "MobileNetV3 Deep Vision" : aiPrediction.source}
              </Text>
            </View>
            <View style={styles.aiResultRow}>
              <Text style={styles.aiCategoryText}>
                {aiPrediction.category.toUpperCase()}
              </Text>
              <Text style={styles.aiConfidenceBadge}>
                {Math.round(aiPrediction.confidence * 100)}% confidence
              </Text>
              <Text
                style={[
                  styles.aiSeverityBadge,
                  aiPrediction.severity === "CRITICAL" || aiPrediction.severity === "HIGH"
                    ? styles.severityHigh
                    : styles.severityNormal,
                ]}
              >
                {aiPrediction.severity}
              </Text>
            </View>
            <Text style={styles.aiCategoryLabel}>Category Confirmation / Override:</Text>
            <View style={styles.categoryChipsRow}>
              {["garbage", "pothole", "drainage", "streetlight", "water_leakage", "other"].map((cat) => (
                <Pressable
                  key={cat}
                  onPress={() => setCategoryOverride(cat)}
                  style={[styles.categoryChip, categoryOverride === cat && styles.categoryChipSelected]}
                >
                  <Text
                    style={[
                      styles.categoryChipText,
                      categoryOverride === cat && styles.categoryChipTextSelected,
                    ]}
                  >
                    {cat}
                  </Text>
                </Pressable>
              ))}
            </View>
          </View>
        ) : null}

        <Pressable
          onPress={submitComplaint}
          disabled={submitting}
          style={[styles.primaryButton, submitting && styles.disabledButton]}
        >
          {submitting ? <ActivityIndicator color="#fff" /> : <Text style={styles.primaryButtonText}>Submit complaint</Text>}
        </Pressable>
      </View>

      <View style={styles.card}>
        <Text style={styles.sectionTitle}>My complaints</Text>
        {complaints.length === 0 ? (
          <Text style={styles.helperText}>No complaints yet. Your newest complaint will appear here.</Text>
        ) : (
          complaints.map((item) => (
            <View key={item.id} style={styles.complaintCard}>
              <View style={styles.statusRow}>
                <Text style={styles.statusText}>{item.status}</Text>
                <Text style={styles.metaText}>{new Date(item.created_at).toLocaleDateString()}</Text>
              </View>
              <Text style={styles.complaintTitle}>{item.title}</Text>
              <View style={styles.categoryBadgeRow}>
                <Text style={styles.metaText}>{item.category.toUpperCase()}</Text>
                {item.classification_source ? (
                  <Text style={styles.aiChip}>
                    🤖 {item.classification_source === "vision_mobilenet_v3" ? "Vision AI" : item.classification_source}
                    {item.category_confidence ? ` · ${Math.round(item.category_confidence * 100)}%` : ""}
                  </Text>
                ) : null}
              </View>
              {item.timeline && item.timeline.length > 0 ? (
                <View style={styles.timelineWrap}>
                  {item.timeline.slice(0, 3).map((event, index) => (
                    <Text key={`${item.id}-${index}`} style={styles.timelineText}>
                      • {event.action} {event.new_status ? `→ ${event.new_status}` : ""}
                    </Text>
                  ))}
                </View>
              ) : null}
              {item.status === "resolution_submitted" ? (
                <View style={styles.decisionRow}>
                  <Pressable onPress={() => void confirmResolution(item.id)} style={styles.primaryButton}>
                    <Text style={styles.primaryButtonText}>Confirm resolution</Text>
                  </Pressable>
                  <Pressable onPress={() => {
                    setRejectingComplaintId(item.id);
                    setRejectionReason("");
                  }} style={styles.secondaryButton}>
                    <Text style={styles.secondaryButtonText}>Request more work</Text>
                  </Pressable>
                  {rejectingComplaintId === item.id ? (
                    <>
                      <TextInput
                        value={rejectionReason}
                        onChangeText={setRejectionReason}
                        placeholder="What still needs to be fixed?"
                        style={[styles.input, styles.textArea]}
                        multiline
                      />
                      <Pressable onPress={() => void rejectResolution(item.id)} style={styles.secondaryButton}>
                        <Text style={styles.secondaryButtonText}>Submit request</Text>
                      </Pressable>
                    </>
                  ) : null}
                </View>
              ) : null}
            </View>
          ))
        )}
      </View>

      <Text style={styles.message}>{message}</Text>
    </ScrollView>
  );
}

type WorkerPortalProps = {
  user: UserSummary;
  tasks: ComplaintSummary[];
  selectedTask: ComplaintSummary | null;
  workerNote: string;
  supportDescription: string;
  resolutionPhoto: ImagePicker.ImagePickerAsset | null;
  submitting: boolean;
  message: string;
  onSignOut: () => void;
  onRefresh: () => void;
  onOpenTask: (taskId: string) => void;
  onStatus: (status: "in_progress" | "resolution_submitted") => void;
  onNoteChange: (value: string) => void;
  onAddNote: () => void;
  onSupportChange: (value: string) => void;
  onRequestSupport: () => void;
  onPickPhoto: () => void;
  onUploadPhoto: () => void;
};

function WorkerPortal({
  user,
  tasks,
  selectedTask,
  workerNote,
  supportDescription,
  resolutionPhoto,
  submitting,
  message,
  onSignOut,
  onRefresh,
  onOpenTask,
  onStatus,
  onNoteChange,
  onAddNote,
  onSupportChange,
  onRequestSupport,
  onPickPhoto,
  onUploadPhoto,
}: WorkerPortalProps) {
  return (
    <ScrollView contentContainerStyle={styles.scrollContent}>
      <View style={styles.headerRow}>
        <View>
          <Text style={styles.title}>Field Worker</Text>
          <Text style={styles.subtitle}>Assigned municipal tasks</Text>
        </View>
        <Pressable onPress={onSignOut}>
          <Text style={styles.linkText}>Sign out</Text>
        </Pressable>
      </View>
      <Text style={styles.greeting}>Welcome, {user.name}</Text>
      <Pressable onPress={onRefresh} style={styles.secondaryButton}>
        <Text style={styles.secondaryButtonText}>Refresh assignments</Text>
      </Pressable>

      <View style={styles.card}>
        <Text style={styles.sectionTitle}>My assignments</Text>
        {tasks.length === 0 ? (
          <Text style={styles.helperText}>No complaints are currently assigned to you.</Text>
        ) : (
          tasks.map((task) => (
            <Pressable key={task.id} onPress={() => onOpenTask(task.id)} style={styles.complaintCard}>
              <View style={styles.statusRow}>
                <Text style={styles.statusText}>{task.status}</Text>
                <Text style={styles.metaText}>{task.category}</Text>
              </View>
              <Text style={styles.complaintTitle}>{task.title}</Text>
              <Text style={styles.metaText}>Priority: {task.priority_score ?? "—"}</Text>
            </Pressable>
          ))
        )}
      </View>

      {selectedTask ? (
        <View style={styles.card}>
          <Text style={styles.sectionTitle}>{selectedTask.title}</Text>
          <Text style={styles.bodyText}>{selectedTask.description}</Text>
          <Text style={styles.metaText}>
            Location: {selectedTask.location_lat ?? "—"}, {selectedTask.location_lng ?? "—"}
          </Text>
          <Text style={styles.statusText}>Status: {selectedTask.status}</Text>
          {selectedTask.images?.map((image) => (
            <Image
              key={`${image.url}-${image.image_type}`}
              source={{ uri: `${API}${image.url}` }}
              style={styles.previewImage}
            />
          ))}

          {selectedTask.status === "assigned" ? (
            <Pressable
              onPress={() => onStatus("in_progress")}
              disabled={submitting}
              style={styles.primaryButton}
            >
              <Text style={styles.primaryButtonText}>Start work</Text>
            </Pressable>
          ) : null}

          <TextInput
            value={workerNote}
            onChangeText={onNoteChange}
            placeholder="Add a work note"
            multiline
            style={[styles.input, styles.textArea]}
          />
          <Pressable onPress={onAddNote} disabled={submitting || !workerNote.trim()} style={styles.secondaryButton}>
            <Text style={styles.secondaryButtonText}>Save worker note</Text>
          </Pressable>

          <TextInput
            value={supportDescription}
            onChangeText={onSupportChange}
            placeholder="Describe additional support needed"
            multiline
            style={[styles.input, styles.textArea]}
          />
          <Pressable
            onPress={onRequestSupport}
            disabled={submitting || !supportDescription.trim()}
            style={styles.secondaryButton}
          >
            <Text style={styles.secondaryButtonText}>Request support</Text>
          </Pressable>

          {selectedTask.status === "in_progress" ? (
            <>
              <Pressable onPress={onPickPhoto} disabled={submitting} style={styles.secondaryButton}>
                <Text style={styles.secondaryButtonText}>Choose resolution photo</Text>
              </Pressable>
              {resolutionPhoto ? (
                <Image source={{ uri: resolutionPhoto.uri }} style={styles.previewImage} />
              ) : null}
              <Pressable
                onPress={onUploadPhoto}
                disabled={submitting || !resolutionPhoto}
                style={styles.primaryButton}
              >
                <Text style={styles.primaryButtonText}>Upload resolution evidence</Text>
              </Pressable>
              <Pressable
                onPress={() => onStatus("resolution_submitted")}
                disabled={submitting || !selectedTask.images?.some((image) => image.image_type === "after")}
                style={styles.primaryButton}
              >
                <Text style={styles.primaryButtonText}>Submit resolution</Text>
              </Pressable>
            </>
          ) : null}
        </View>
      ) : null}
      <Text style={styles.message}>{message}</Text>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  shell: {
    flex: 1,
    justifyContent: "center",
    padding: 24,
    backgroundColor: "#f4f1ea",
  },
  scrollContent: {
    padding: 24,
    backgroundColor: "#f4f1ea",
    gap: 16,
  },
  title: {
    fontSize: 28,
    fontWeight: "700",
    color: "#1b2c2a",
  },
  subtitle: {
    fontSize: 16,
    color: "#4a5d59",
    marginBottom: 12,
  },
  greeting: {
    fontSize: 18,
    fontWeight: "600",
    color: "#1b2c2a",
  },
  input: {
    borderWidth: 1,
    borderColor: "#d4d6cf",
    backgroundColor: "#ffffff",
    borderRadius: 10,
    paddingHorizontal: 14,
    paddingVertical: 12,
    color: "#1b2c2a",
    marginBottom: 12,
  },
  textArea: {
    minHeight: 120,
    textAlignVertical: "top",
  },
  fieldRow: {
    flexDirection: "row",
    gap: 12,
  },
  inlineInput: {
    flex: 1,
  },
  primaryButton: {
    backgroundColor: "#1f4d3a",
    borderRadius: 10,
    paddingVertical: 14,
    alignItems: "center",
    justifyContent: "center",
    marginTop: 8,
  },
  primaryButtonText: {
    color: "#ffffff",
    fontWeight: "700",
  },
  secondaryButton: {
    backgroundColor: "#e9efe8",
    borderRadius: 10,
    paddingVertical: 12,
    alignItems: "center",
    marginBottom: 12,
  },
  secondaryButtonText: {
    color: "#1b2c2a",
    fontWeight: "600",
  },
  decisionRow: {
    gap: 4,
    marginTop: 8,
  },
  card: {
    backgroundColor: "#ffffff",
    borderRadius: 14,
    padding: 16,
    borderColor: "#e6e8e2",
    borderWidth: 1,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: "700",
    marginBottom: 10,
    color: "#1b2c2a",
  },
  helperText: {
    color: "#4a5d59",
    fontSize: 13,
  },
  previewWrap: {
    marginBottom: 12,
  },
  previewImage: {
    width: "100%",
    height: 180,
    borderRadius: 10,
    backgroundColor: "#dfe6df",
  },
  complaintCard: {
    borderWidth: 1,
    borderColor: "#e5e7e3",
    borderRadius: 12,
    padding: 12,
    marginTop: 10,
    backgroundColor: "#f7f8f5",
  },
  statusRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 8,
  },
  statusText: {
    fontWeight: "700",
    color: "#173f30",
    textTransform: "capitalize",
  },
  metaText: {
    color: "#586864",
    fontSize: 12,
  },
  complaintTitle: {
    fontSize: 16,
    fontWeight: "700",
    marginBottom: 4,
    color: "#1b2c2a",
  },
  bodyText: {
    color: "#334e49",
    marginBottom: 10,
    lineHeight: 20,
  },
  timelineWrap: {
    marginTop: 8,
    gap: 4,
  },
  timelineText: {
    color: "#38544e",
    fontSize: 12,
  },
  message: {
    marginTop: 12,
    color: "#39524d",
  },
  linkText: {
    color: "#1f4d3a",
    fontWeight: "700",
  },
  headerRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  disabledButton: {
    opacity: 0.6,
  },
  // AI prediction card styles
  aiLoadingCard: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    padding: 14,
    backgroundColor: "#eef6f2",
    borderRadius: 10,
    marginBottom: 12,
  },
  aiLoadingText: {
    color: "#1f4d3a",
    fontSize: 13,
    fontWeight: "600",
  },
  aiPredictionCard: {
    backgroundColor: "#eef6f2",
    borderRadius: 12,
    padding: 14,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: "#c5ddd2",
  },
  aiHeaderRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 10,
  },
  aiTag: {
    fontSize: 13,
    fontWeight: "700",
    color: "#1f4d3a",
  },
  aiSourceBadge: {
    fontSize: 10,
    fontWeight: "700",
    color: "#2563eb",
    backgroundColor: "#dbeafe",
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 8,
    overflow: "hidden",
  },
  aiResultRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    flexWrap: "wrap",
    marginBottom: 10,
  },
  aiCategoryText: {
    fontSize: 16,
    fontWeight: "700",
    color: "#1b2c2a",
  },
  aiConfidenceBadge: {
    fontSize: 11,
    fontWeight: "700",
    color: "#ffffff",
    backgroundColor: "#2563eb",
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 10,
    overflow: "hidden",
  },
  aiSeverityBadge: {
    fontSize: 11,
    fontWeight: "700",
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 10,
    overflow: "hidden",
  },
  severityHigh: {
    backgroundColor: "#b91c1c",
    color: "#ffffff",
  },
  severityNormal: {
    backgroundColor: "#15803d",
    color: "#ffffff",
  },
  aiCategoryLabel: {
    fontSize: 12,
    fontWeight: "600",
    color: "#4a5d59",
    marginBottom: 6,
  },
  categoryChipsRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 6,
  },
  categoryChip: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
    backgroundColor: "#ffffff",
    borderWidth: 1,
    borderColor: "#d4d6cf",
  },
  categoryChipSelected: {
    backgroundColor: "#1f4d3a",
    borderColor: "#1f4d3a",
  },
  categoryChipText: {
    fontSize: 12,
    fontWeight: "600",
    color: "#1b2c2a",
    textTransform: "capitalize",
  },
  categoryChipTextSelected: {
    color: "#ffffff",
  },
  categoryBadgeRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    flexWrap: "wrap",
    marginTop: 4,
  },
  aiChip: {
    fontSize: 10,
    fontWeight: "700",
    color: "#2563eb",
    backgroundColor: "#eff6ff",
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 8,
    overflow: "hidden",
  },
});
