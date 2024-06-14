using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using NativeWebSocket;
using Newtonsoft.Json;
using System.Threading.Tasks;

public class WebSocketClient : MonoBehaviour
{
    public GameObject mapTileRightPrefab;
    public GameObject mapTileDownPrefab;
    public GameObject mapTileLeftPrefab;
    public GameObject mapTileUpPrefab;
    public GameObject obstaclePrefab;
    public GameObject carPrefab;
    public GameObject stopSignPrefab;
    public Transform mapPanel;

    private WebSocket websocket;
    private GameObject carInstance;
    private List<GameObject> stopSignInstances = new List<GameObject>();

    private int[,] mapArray;
    private Vector2Int carPosition;
    private List<Vector2Int> stopSignPositions = new List<Vector2Int>();

    async void Start()
    {
        websocket = new WebSocket("ws://localhost:8765");

        websocket.OnOpen += () =>
        {
            Debug.Log("¡Conexión abierta!");
        };

        websocket.OnError += (e) =>
        {
            Debug.Log("¡Error! " + e);
        };

        websocket.OnClose += (e) =>
        {
            Debug.Log("¡Conexión cerrada!");
        };

        websocket.OnMessage += (bytes) =>
        {
            // Leer un mensaje de texto simple
            var message = System.Text.Encoding.UTF8.GetString(bytes);
            Debug.Log("¡Mensaje recibido! " + message);
            HandleMessage(message);
        };

        await websocket.Connect();

        // Invocar repetidamente para solicitar actualizaciones
        InvokeRepeating(nameof(SendWebSocketMessage), 0.0f, 0.5f);
    }

    async void SendWebSocketMessage()
    {
        if (websocket.State == WebSocketState.Open)
        {
            await websocket.SendText("Solicitando actualización");
        }
    }

    private void HandleMessage(string message)
    {
        var data = JsonConvert.DeserializeObject<Dictionary<string, object>>(message);

        if (data.ContainsKey("map"))
        {
            mapArray = JsonConvert.DeserializeObject<int[,]>(data["map"].ToString());
            carPosition = JsonConvert.DeserializeObject<List<int>>(data["car_position"].ToString()).ToVector2Int();
            stopSignPositions = JsonConvert.DeserializeObject<List<List<int>>>(data["stopsign_positions"].ToString()).ConvertAll(pos => new Vector2Int(pos[1], pos[0]));
            InitializeMap();
        }
        else if (data.ContainsKey("car_position"))
        {
            carPosition = JsonConvert.DeserializeObject<List<int>>(data["car_position"].ToString()).ToVector2Int();
            UpdateCarPosition();
        }
    }

    private void InitializeMap()
    {
        // Limpiar tiles de mapa y señales de stop anteriores
        foreach (Transform child in mapPanel)
        {
            Destroy(child.gameObject);
        }
        stopSignInstances.Clear();

        // Inicializar el mapa basado en mapArray
        for (int y = 0; y < mapArray.GetLength(0); y++)
        {
            for (int x = 0; x < mapArray.GetLength(1); x++)
            {
                GameObject tile = null;
                switch (mapArray[y, x])
                {
                    case 1:
                        tile = Instantiate(mapTileRightPrefab, mapPanel);
                        break;
                    case 2:
                        tile = Instantiate(mapTileDownPrefab, mapPanel);
                        break;
                    case 3:
                        tile = Instantiate(mapTileLeftPrefab, mapPanel);
                        break;
                    case 4:
                        tile = Instantiate(mapTileUpPrefab, mapPanel);
                        break;
                    case 0:
                    default:
                        tile = Instantiate(obstaclePrefab, mapPanel);
                        break;
                }

                if (tile != null)
                {
                    // Posicionar el tile en (x, -y) para coincidir con el sistema de coordenadas de Unity
                    tile.transform.localPosition = new Vector3(x, -y, 0);
                    tile.transform.localScale = new Vector3(1, 1, 1);
                    // Establecer orden de clasificación para carriles y obstáculos
                    var spriteRenderer = tile.GetComponent<SpriteRenderer>();
                    if (spriteRenderer != null)
                    {
                        spriteRenderer.sortingOrder = 0; // Capa 0 para carriles y obstáculos
                    }
                }
            }
        }

        // Inicializar señales de stop
        foreach (var stopSign in stopSignPositions)
        {
            var stopSignInstance = Instantiate(stopSignPrefab, mapPanel);
            stopSignInstance.transform.localPosition = new Vector3(stopSign.x, -stopSign.y, 0);
            stopSignInstance.transform.localScale = new Vector3(1, 1, 1);
            // Establecer orden de clasificación para señales de stop
            var spriteRenderer = stopSignInstance.GetComponent<SpriteRenderer>();
            if (spriteRenderer != null)
            {
                spriteRenderer.sortingOrder = 1; // Capa 1 para señales de stop
            }
            stopSignInstances.Add(stopSignInstance);
        }

        // Inicializar el coche
        if (carInstance == null)
        {
            carInstance = Instantiate(carPrefab, mapPanel);
        }
        carInstance.transform.localPosition = new Vector3(carPosition.x, -carPosition.y, 0);
        carInstance.transform.localScale = new Vector3(1, 1, 1);
        // Establecer orden de clasificación para el coche
        var carSpriteRenderer = carInstance.GetComponent<SpriteRenderer>();
        if (carSpriteRenderer != null)
        {
            carSpriteRenderer.sortingOrder = 2; // Capa 2 para el coche
        }
    }

    private void UpdateCarPosition()
    {
        if (carInstance != null)
        {
            carInstance.transform.localPosition = new Vector3(carPosition.x, -carPosition.y, 0);
        }
    }

    private async void OnApplicationQuit()
    {
        await websocket.Close();
    }

    void Update()
    {
#if !UNITY_WEBGL || UNITY_EDITOR
        websocket.DispatchMessageQueue();
#endif
    }
}

public static class Extensions
{
    public static Vector2Int ToVector2Int(this List<int> list)
    {
        if (list == null || list.Count < 2) return Vector2Int.zero;
        return new Vector2Int(list[1], list[0]); // Orden correcto
    }
}
