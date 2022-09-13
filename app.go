package main

// import "camalot/hdhomerun-api/cmd"
import (
	"context"
	"flag"
	"fmt"
	"log"
	"net/http"
	"io/ioutil"
	"regexp"
	"os"
	"encoding/json"
	// "os/signal"
	// "syscall"
	"time"
	"strconv"
	"github.com/prometheus/client_golang/prometheus"
	// "github.com/prometheus/client_golang/prometheus/promauto"
	"github.com/prometheus/client_golang/prometheus/promhttp"
	"gopkg.in/yaml.v3"
)


func getUrl(tuner Tuner, path string) string {
	scheme := "http"
	if tuner.UseTLS {
		scheme = "https"
	}
	url := fmt.Sprintf("%s://%s/%s", scheme, tuner.Hostname, path)
	return url
}

func getRequestBody(url string) ([]byte,error) {
	httpClient := http.Client{
		Timeout: time.Second * 5, // Timeout after 2 seconds
	}
	req, err := http.NewRequest(http.MethodGet, url, nil)
	if err != nil {
		// log.Fatal(err)
		return nil, err
	}
	res, getErr := httpClient.Do(req)
	if getErr != nil {
		// log.Fatal(getErr)
		return nil, getErr
	}

	if res.Body != nil {
		defer res.Body.Close()
	}

	body, readErr := ioutil.ReadAll(res.Body)
	if readErr != nil {
		// log.Fatal(readErr)
		return nil, readErr
	}
	return body, nil
}

// var totalRequests = prometheus.NewGaugeVec(
// 	prometheus.CounterOpts{
// 		Name: "http_requests_total",
// 		Help: "Number of get requests.",
// 	},
// 	[]string{"path"},
// )
func getTuners(config Config) {
	for i := range config.Tuners {
		t := config.Tuners[i]
		url := getUrl(t,"tuners.html")
		body, err := getRequestBody(url)
		if err != nil {
			continue
		}
		content := string(body[:])
		re := regexp.MustCompile(`<tr>\s*<td>(?P<tuner>[^<]+)</td>\s*<td>(?P<state>[^<]+)</td></tr>`)
		matches := re.FindAllString(content, -1)
		inUse := 0
		totalTuners := 0
		for i := range matches {

			submatches := re.FindStringSubmatch(matches[i])
			// tunerIndex := re.SubexpIndex("tuner")
			stateIndex := re.SubexpIndex("state")
			if ( submatches[stateIndex] != "none" && submatches[stateIndex] != "not in use" ) {
				inUse++
			}
			totalTuners++
		}
		if err := prometheus.Register(prometheus.NewGaugeFunc(
			prometheus.GaugeOpts{
				Namespace:   "hdhomerun",
				Name:        "tuners_available_total",
				Help:        "number of tuners this host has.",
				ConstLabels: prometheus.Labels{"host": t.Hostname},
			},
			func() float64 { return float64(totalTuners) },
		)); err == nil {
			fmt.Println(`GaugeFunc 'hdhomerun_tuners_available_total' for registered with labels {destination="%s"}`, t.Hostname)
		}
		if err := prometheus.Register(prometheus.MustNewGaugeFunc(
			prometheus.GaugeOpts{
				Namespace:   "hdhomerun",
				Name:        "tuners_in_use",
				Help:        "number of tuners currently in use.",
				ConstLabels: prometheus.Labels{"host": t.Hostname},
			},
			func() float64 { return float64(inUse) },
		)); err == nil {
			fmt.Println(`GaugeFunc 'hdhomerun_tuners_in_use' for registered with labels {destination="%s"}`, t.Hostname)
		}
		if err := prometheus.Register(prometheus.MustNewGaugeFunc(
			prometheus.GaugeOpts{
				Namespace:   "hdhomerun",
				Name:        "tuners_available",
				Help:        "number of tuners available for use.",
				ConstLabels: prometheus.Labels{"host": t.Hostname},
			},
			func() float64 { return float64(totalTuners - inUse) },
		)); err == nil {
			fmt.Println(`GaugeFunc 'hdhomerun_tuners_available' for registered with labels {destination="%s"}`, t.Hostname)
		}
	}
}

func getUpdateStatus(config Config) {
	for i := range config.Tuners {
		t := config.Tuners[i]
		url := getUrl(t,"upgrade_status.json")
		body, err := getRequestBody(url)
		if err != nil {
			continue
		}

		status := UpgradeStatus{}
		jsonErr := json.Unmarshal(body, &status)
		if jsonErr != nil {
			log.Fatal(jsonErr)
		}
		hasUpgrade := status.UpgradeAvailable == 1
		log.Printf(url)
		log.Printf("Has Upgrade: %b", hasUpgrade)
		if err := prometheus.Register(prometheus.NewGaugeFunc(
			prometheus.GaugeOpts{
				Namespace:   "hdhomerun",
				Name:        "upgrade_available",
				Help:        "tuner has updates available.",
				ConstLabels: prometheus.Labels{"host": t.Hostname},
			},
			func() float64 { return float64(status.UpgradeAvailable) },
		)); err == nil {
			fmt.Println(`GaugeFunc 'hdhomerun_upgrade_available' for registered with labels {destination="%s"}`, t.Hostname)
		}
	}
}

func getChannels (config Config) {
	for i := range config.Tuners {
		t := config.Tuners[i]
		url := getUrl(t,"lineup.json?show=found")
		body, err := getRequestBody(url)
		if err != nil {
			continue
		}

		channels := []GuideChannel{}
		jsonErr := json.Unmarshal(body, &channels)
		if jsonErr != nil {
			log.Fatal(jsonErr)
		}

		log.Printf(url)
		log.Printf("Total Channels: %d", len(channels))
		if err := prometheus.Register(prometheus.NewGaugeFunc(
			prometheus.GaugeOpts{
				Namespace:   "hdhomerun",
				Name:        "channels_available",
				Help:        "Number of available channels on a tuner.",
				ConstLabels: prometheus.Labels{"host": t.Hostname},
			},
			func() float64 { return float64(len(channels)) },
		)); err == nil {
			fmt.Println(`GaugeFunc 'hdhomerun_channels_available' for registered with labels {destination="%s"}`, t.Hostname)
		}
	}
}

type TunerStatus struct {
	Available int
	Used int
}

type UpgradeStatus struct {
	UpgradeAvailable int `json:UpgradeAvailable`
}

type GuideChannel struct {
	GuideNumber string `json:GuideNumber`
	GuideName string `json:GuideName`
	VideoCodec string `json:VideoCodec`
	AudioCodec string `json:AudioCodec`
}

type Tuner struct {
	Hostname string `yaml:hostname`
	UseTLS bool `yaml:useTLS`
	ValidateTLS bool `yaml:validateTLS`
}

type Config struct {
	Metrics struct {
		Port int `yaml:port`
		// Timeout struct {
		// 	// Server is the general server timeout to use
		// 	// for graceful shutdowns
		// 	Server time.Duration `yaml:"server"`

		// 	// Write is the amount of time to wait until an HTTP server
		// 	// write opperation is cancelled
		// 	Write time.Duration `yaml:"write"`

		// 	// Read is the amount of time to wait until an HTTP server
		// 	// read operation is cancelled
		// 	Read time.Duration `yaml:"read"`

		// 	// Read is the amount of time to wait
		// 	// until an IDLE HTTP session is closed
		// 	Idle time.Duration `yaml:"idle"`
		// } `yaml:"timeout"`
	} `yaml:metrics`
	Tuners []Tuner `yaml:tuners`
}

func ParseFlags() (string, error) {
    // String that contains the configured configuration path
    var configPath string
    // Set up a CLI flag called "-config" to allow users
    // to supply the configuration file
    flag.StringVar(&configPath, "config", "./.hdhomerun-cli.yml", "path to config file")
    // Actually parse the flags
    flag.Parse()
    // Validate the path first
    if err := ValidateConfigPath(configPath); err != nil {
        return "", err
    }

    // Return the configuration path
    return configPath, nil
}

// ValidateConfigPath just makes sure, that the path provided is a file,
// that can be read
func ValidateConfigPath(path string) error {
    s, err := os.Stat(path)
    if err != nil {
        return err
    }
    if s.IsDir() {
        return fmt.Errorf("'%s' is a directory, not a normal file", path)
    }
    return nil
}

func NewConfig(configPath string) (*Config, error) {
    // Create config structure
    config := &Config{}

    // Open config file
    file, err := os.Open(configPath)
    if err != nil {
        return nil, err
    }
    defer file.Close()

    // Init new YAML decode
    d := yaml.NewDecoder(file)

    // Start YAML decoding from file
    if err := d.Decode(&config); err != nil {
        return nil, err
    }

    return config, nil
}


func MetricsRouter() *http.ServeMux {
    // Create router and define routes and return that router
    router := http.NewServeMux()
    router.Handle("/metrics", promhttp.Handler())
    return router
}

func ProbeRouter() *http.ServeMux {
    // Create router and define routes and return that router
    router := http.NewServeMux()
    router.Handle("/probe", promhttp.Handler())
    return router
}

func (config Config) RecordMetrics (){
	go func() {
		for {
			getChannels(config)
			getUpdateStatus(config)
			getTuners(config)
			time.Sleep(time.Minute * 10) // update every 10 minutes
		}
	}()
}

type MyCollector struct {
  counterDesc *prometheus.Desc
}

func (c *MyCollector) Describe(ch chan<- *prometheus.Desc) {
  ch <- c.counterDesc
}

func (c *MyCollector) Collect(ch chan<- prometheus.Metric) {
  value := 1.0 // Your code to fetch the counter value goes here.
  ch <- prometheus.MustNewConstMetric(
    c.counterDesc,
    prometheus.CounterValue,
    value,
  )
}

func NewMyCollector() *MyCollector {
  return &MyCollector{
    counterDesc: prometheus.NewDesc("my_counter_total", "Help string", nil, nil),
  }
}

// To hook in the collector: prometheus.MustRegister(NewMyCollector())

func (config Config) Run() {
	// Set up a channel to listen to for interrupt signals
	var runChan = make(chan os.Signal, 1)
	// Set up a context to allow for graceful server shutdowns in the event
	// of an OS interrupt (defers the cancel just in case)
	ctx, cancel := context.WithTimeout(
		context.Background(),
		30,
		// config.Metrics.Timeout.Server,
	)
	defer cancel()

    // Define server options
	server := &http.Server{
		Addr:         ":" + strconv.Itoa(config.Metrics.Port),
		Handler:      MetricsRouter(),
		// ReadTimeout:  config.Metrics.Timeout.Read * time.Second,
		// WriteTimeout: config.Metrics.Timeout.Write * time.Second,
		// IdleTimeout:  config.Metrics.Timeout.Idle * time.Second,
	}
	// Handle ctrl+c/ctrl+x interrupt
	// signal.Notify(runChan, os.Interrupt, syscall.SIGTSTP)

	// Alert the user that the server is starting
	log.Printf("Server is starting on %s\n", server.Addr)

	// Run the server on a new goroutine
	go func() {
		if err := server.ListenAndServe(); err != nil {
			if err == http.ErrServerClosed {
				// Normal interrupt operation, ignore
			} else {
				log.Fatalf("Server failed to start due to err: %v", err)
			}
		}
	}()

	// Block on this channel listeninf for those previously defined syscalls assign
	// to variable so we can let the user know why the server is shutting down
	interrupt := <-runChan

	// If we get one of the pre-prescribed syscalls, gracefully terminate the server
	// while alerting the user
	log.Printf("Server is shutting down due to %+v\n", interrupt)
	if err := server.Shutdown(ctx); err != nil {
		log.Fatalf("Server was unable to gracefully shutdown due to err: %+v", err)
	}
}

func main() {
		// Generate our config based on the config supplied
    // by the user in the flags
    cfgPath, err := ParseFlags()
    if err != nil {
        log.Fatal(err)
    }
    cfg, err := NewConfig(cfgPath)
    if err != nil {
        log.Fatal(err)
    }
		cfg.RecordMetrics()
    // Run the server
    cfg.Run()
}
