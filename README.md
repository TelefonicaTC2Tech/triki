# Triki

Cookie analysis automation using [Selenium](https://selenium-python.readthedocs.io/).

It uses a yaml configuration file to perform actions over a list of sites where we want to analyze its cookie usage.

## Table of contents

- [Triki](#triki)
  - [Table of contents](#table-of-contents)
  - [Install Triki](#install-triki)
    - [Prerequisites](#prerequisites)
    - [Mac users](#mac-users)
    - [Windows users](#windows-users)
    - [Virtual Environment](#virtual-environment)
    - [Dependencies](#dependencies)
    - [Output](#output)
  - [Configuration file](#configuration-file)
    - [Locate WebElements](#locate-webelements)
    - [Click events](#click-events)
    - [Keyboard events](#keyboard-events)
    - [Navigate between frames](#navigate-between-frames)
    - [Screenshots](#screenshots)
    - [Waits](#waits)
  - [Analysis and stats](#analysis-and-stats)
  - [Known issues](#known-issues)
  - [Contributors](#contributors)
  - [License](#license)

## Install Triki

### Prerequisites

- python 3.7+
- virtualenv (not required but highly recommended)
- [chromedriver](https://chromedriver.chromium.org/downloads) on your path

We have tested `Triki` using chrome as the automated browser, though this can be changed to other browsers, for more information around that check the [selenium installation driver section](https://selenium-python.readthedocs.io/installation.html)

### Mac users

Assuming you have `homebrew` installed you can run

```
brew cask install chromedriver
```

In using Catalina or above allow the exception in `preferences->Security&Privacy` so that chromedriver con be executed not being an official app store app.

### Windows users

Environment Variables:

Este equipo -> Propiedades (Botón derecho) -> Configuración avanzada del sistema -> Variables de entorno -> Variables del sistema -> Path (seleccionar) -> Editar -> Nuevo -> _\<Path de chromedrive.exe\>_ (ej: _C:\chrome\\_).

### Virtual Environment

It is advisable to use a separate virtual environment. To instantiate a virtual environment with virtualenv.

```
virtualenv -p `which python3` <yourenvname>
```

To activate the virtual environment on your terminal just type:

```
source <yourenvname>/bin/activate
```

### Dependencies

The easiest way of getting the system up and running is to install the dependencies this way

```
pip install -r requirements.txt
```

The list of dependencies are the following:

- arrow
- selenium
- pyyaml

These other dependencies are used for development:

- black

## Run Triki

First you should check `sites-example.yaml` inside the `config` folder, rename it to `sites.yaml` and adapt or extend to your needs. For more info around this check the [Configuration file section](#configuration-file)

Once you have done that, you can run `Triki` over your desired list of sites by running:

```
./triki.py
```

### Output

After the script has been run there will be a `data` folder that contains a folder for each unique `site`. Inside that folder with each `date` where `Triki` has been executed (we do this to be able to track changes over time for a given list of sites).

Inside each iteration (date folder) you will find:

- The screenshots that you have configured to be done by selenium
- a `csv` file for each `flow_type` executed over a site with the list of cookies that have been stored on the browser. (first and third party)
- a `csv` file with some statistics over the cookies that have been found: such as average expiration time, total number of cookies, number of sessión cookies, etc.

## Configuration file

We provide `config\sites-example.yaml` as an example configuration file in order to jump start the use of `Triki` for your own purposes regarding cookie analysis.

Triki's capabilities are heavily based on those of the selenium project for browser automation.

Triki exposes the majority of those functionalities needed to analyze the cookies setup by different sites.

The posible interaction with the page can be divided as follows:

### Locate WebElements

Selenium can use ids, classes or xpaths to [locate elements](https://selenium-python.readthedocs.io/locating-elements.html) and then perform some action on them (click, etc). You'll need to respect the selection options that selenium offers like: "tag name", "class name", "id", etc.

For example using the id to locate the element:

```yaml
- {
    element: { by: "id", value: "didomi-notice-learn-more-button" },
    action: "click",
  }
```

We have adapted the syntax the selenium provides accepting either a single or multiple elements, if multiple elements are given we use the text of the element to determine which one we should perform the action in. For example:

```yaml
- {
    element:
      {
        by: "class name",
        value: "didomi-components-button",
        multiple: True,
        match: "Configurar",
      },
    action: "click",
  }
```

### Click events

Selenium can perform clicks in order to automate user behavior on the browser. The default option is performing a `mouse click event` on a given element. For example:

```yaml
- {
    element:
      { by: "tag name", value: "button", multiple: True, match: "Configurar" },
    action: "click",
  }
```

But in some cases `javascript`is needed to make that action in some pages, in that case we need to reflect that in the configuration file, for example:

```yaml
- {
    element: { by: "id", value: "gdprcookieDeny_publicidad", javascript: True },
    action: "click",
  }
```

### Keyboard events

Selenium is able to simulate user input to fill in input fields such as in a login form. In our configuration file you can use this functionality like this:

```yaml
- { element: { by: "name", value: "q" }, action: "keys", value: "tegra" }
```

### Submit forms

If you perform a submit on an element within a form, WebDriver will walk up the DOM until it finds the enclosing form and then calls submit on that.

```yaml
- { element: { by: "name", value: "q" }, action: "submit" }
```

### Navigate between frames

Sometimes cookie banners are available inside an iframe when the site uses a third party to provide that service, in order to be able to interact with a different window or frame you first need to switch to it. For example using and `xpath` to locate the desired frame:

```yaml
- {
    element: { by: "xpath", value: "/html/body/div[5]/div/iframe" },
    action: "navigate_frame",
  }
```

### Screenshots

Selenium allows you to take screenshots from the actual page being automated, you can take a screenshot of the whole page or select the screenshot of a given element and all of its children.

Whole site:

```yaml
- { element: null, action: "screenshot", filename: "site" }
```

An element, such as the cookie banner:

```yaml
- {
    element: { by: "class name", value: "cookie-announce" },
    action: "screenshot",
    filename: "banner",
  }
```

### Waits

Selenium provides some utility methods to be able to wait for some elements or events on the page to happen before performing the given action. Sometimes you need to wait for the whole page to load because of delays in asynchronous calls.

We have adapted the syntax to include it in our configuration file for the most common wait scenarios.

If no element is passed in the configuration, selenium will perform an explicit wait of x seconds as provided in the config:

```yaml
- { element: None, action: "delay", value: 5 }
```

If an element is given the default condition is for the element to be clickable, For example:

```yaml
- {
    element: { by: "class name", value: "tw-flex-grow-0" },
    action: "delay",
    value: 5,
  }
```

You can pass other conditions like:

- element_to_be_clickable
- presence_of_element_located
- visibility_of_element_located

For example using a wait for the presence of an element to be located could be like this:

```yaml
- {
    element:
      {
        by: "id",
        value: "gdprcookieDeny_publicidad",
        condition: "presence_of_element_located",
      },
    action: "delay",
    value: 5,
  }
```

Finally, let us show a complete example with the three identified flow types for ElevenPaths site:

```yaml
sites:
  - url: https://www.elevenpaths.com
    flow_type: browse
    flow:
      - { element: null, action: "sleep", value: 30 }
  - url: https://www.elevenpaths.com
    flow_type: accept
    flow:
      - { element: null, action: "delay", value: 5 }
      - { element: null, action: "screenshot", filename: "site" }
      - {
          element: { by: "id", value: "onetrust-banner-sdk" },
          action: "screenshot",
          filename: "message",
        }
      - {
          element: { by: "id", value: "onetrust-accept-btn-handler" },
          action: "delay",
          value: 5,
        }
      - {
          element: { by: "id", value: "onetrust-accept-btn-handler" },
          action: "click",
        }
      - { element: null, action: "sleep", value: 30 }
  - url: https://www.elevenpaths.com
    flow_type: reject
    flow:
      - { element: null, action: "delay", value: 5 }
      - {
          element: { by: "id", value: "onetrust-pc-btn-handler" },
          action: "delay",
          value: 5,
        }
      - {
          element: { by: "id", value: "onetrust-pc-btn-handler" },
          action: "click",
        }
      - { element: null, action: "sleep", value: 5 }
      - {
          element: { by: "id", value: "onetrust-banner-sdk" },
          action: "screenshot",
          filename: "configuration",
        }
      - {
          element: { by: "class name", value: "ot-pc-refuse-all-handler" },
          action: "delay",
          value: 5,
        }
      - {
          element: { by: "class name", value: "ot-pc-refuse-all-handler" },
          action: "click",
        }
      - { element: null, action: "sleep", value: 30 }
```

## Analysis and stats

Inside `Triki` there's an analysis folder with two auxiliary scripts that will ease the cookie analysis phase:

- Moving all the output results into and SQLite database
- Comparing the number of clicks needed to reject or accept cookies using the configuration file `config\sites.yaml` as an input.

For more information around the analysis scripts check its own [README](analysis/README.md) file.

## Known issues

As we continue to test sites new functionality will be needed that allows a more complex interactions with the site page, we will need to create a grammar in the config file that allows us to translate into the [navigation options](https://selenium-python.readthedocs.io/navigating.html) inside selenium.

Contributions to `Triki` in order to make it more robust are more than welcome, feel free to send as a `pull request`

## Contributors

TEGRA is an R&D Cybersecurity Center based in Galicia (Spain). It is a joint effort from Telefónica, a leading international telecommunications company, through ElevenPaths, its global cybersecurity unit, and Gradiant, an ICT R&D center with more than 100 professionals working in areas like connectivity, security and intelligence, to create innovative products and services inside cybersecurity.

TEGRA's work is focused on two areas within the cybersecurity landscape: Data Security and Security Analytics. We are committed to creating state-of-the-art technologies that can nurture and thus provide differentiating value to our products.

See the [CONTRIBUTORS](CONTRIBUTORS) file.

## License

`Triki`is released under MIT license. For more info check the [LICENSE](LICENSE) file.
