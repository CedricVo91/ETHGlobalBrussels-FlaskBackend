from flask import Flask
from flask import jsonify
from sklearn.cluster import KMeans
from flask_cors import CORS
from urllib.request import urlretrieve, urlopen
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import io
import base64
from flask import send_file
from sklearn.decomposition import PCA
from flask import request
from flask_cors import cross_origin
from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport
from pandasql import sqldf
app = Flask(__name__)

pysqldf = lambda q: sqldf(q, globals())
CORS(app, resources=r'/api/*')

app.config['CORS_HEADERS'] = 'Content-Type'

@app.route("/api/")
def hello_world():
    return jsonify("test")

@app.route("/api/basic_data")
async def basic_data():
    with urlopen('https://gateway.lighthouse.storage/ipfs/' + request.args.get('cid')) as f: # Download File
        df = pd.read_csv(f)

        # Summary Statistics
        summary = df.describe().to_dict()

        # Missing Values
        missing_values = df.isnull().sum().to_dict()

        # Unique Values
        unique_values = df.nunique().to_dict()

        # Histograms
        histograms = {}
        for column in df.select_dtypes(include=['number']).columns:
            plt.figure()
            df[column].hist()
            plt.title(f'Histogram of {column}')
            plt.xlabel(column)
            plt.ylabel('Frequency')

            img = io.BytesIO()
            plt.savefig(img, format='png')
            img.seek(0)
            histograms[column] = base64.b64encode(img.getvalue()).decode()
            plt.close()

        # # Correlation Matrix
        plt.figure(figsize=(10, 8))
        corr = df.corr()
        sns.heatmap(corr, annot=True, fmt='.2f', cmap='coolwarm', vmin=-1, vmax=1)
        plt.title('Correlation Matrix')

        img = io.BytesIO()
        plt.savefig(img, format='png')
        img.seek(0)
        correlation_matrix = base64.b64encode(img.getvalue()).decode()
        plt.close()

        return jsonify({
            'summary': summary,
            'missing_values': missing_values,
            'unique_values': unique_values,
            # 'histograms': histograms,
            # 'correlation_matrix': correlation_matrix
        })
@app.route('/api/basic_data_corr')
async def basic_data_corr():
    with urlopen('https://gateway.lighthouse.storage/ipfs/' + request.args.get('cid')) as f: # Download File

        df = pd.read_csv(f)
         # # Correlation Matrix
        plt.figure(figsize=(10, 8))
        corr = df.corr()
        sns.heatmap(corr, annot=True, fmt='.2f', cmap='coolwarm', vmin=-1, vmax=1)
        plt.title('Correlation Matrix')

        img = io.BytesIO()
        plt.savefig(img, format='png')
        img.seek(0)
        # correlation_matrix = base64.b64encode(img.getvalue()).decode('utf-8')
        plt.close()
        return send_file(img, mimetype='image/png')
        # return jsonify({"image":correlation_matrix})


@app.route('/api/pca')
async def pca():

    """
    Perform PCA on the provided dataset to determine feature importance.

    Parameters:
    data (list of dict): List of dictionaries containing the dataset.
    n_components (int): Number of principal components to compute. Default is None, which means all components are computed.

    Returns:
    dict: A dictionary containing the explained variance ratio and feature importance.
    """

    with urlopen('https://gateway.lighthouse.storage/ipfs/' + request.args.get('cid')) as f: # Download File
        n_components = 3
        df = pd.read_csv(f)
        numeric_features = df.select_dtypes(include='number').columns.tolist()
        selected_features = df[numeric_features]

        # Perform PCA
        pca = PCA(n_components=n_components)
        pca.fit(selected_features)

        explained_variance_ratio = pca.explained_variance_ratio_
        feature_importance = pd.DataFrame(pca.components_, columns=numeric_features).abs().mean().sort_values(ascending=False)

        pca_result = {
            'explained_variance_ratio': explained_variance_ratio.tolist(),
            'feature_importance': feature_importance.to_dict()
        }
        # Create DataFrame for explained variance ratio
        explained_variance_df = pd.DataFrame({
            'Principal Component': [f'PC{i+1}' for i in range(len(pca_result['explained_variance_ratio']))],
            'Explained Variance Ratio': pca_result['explained_variance_ratio']
        })
        # Create DataFrame for feature importance
        feature_importance_df = pd.DataFrame(list(pca_result['feature_importance'].items()), columns=['Feature', 'Importance'])

        # Display explained variance ratio as HTML table
        # return (explained_variance_df.to_html(classes='table table-striped', index=False), feature_importance_df.to_html(classes='table table-striped', index=False))
        return jsonify(explained_variance_df.to_dict())


@app.route("/api/2dkmeans")
def knn(url:str, feature_x:str, feature_y:str):

    with urlopen(url,) as f: # Download File
        n_clusters = 3
        df = pd.read_csv(f)
        selected_features = df[[feature_x, feature_y]]

        kmeans = KMeans(n_clusters=n_clusters)
        df['cluster'] = kmeans.fit_predict(selected_features)

        plt.figure(figsize=(8, 6))
        plt.scatter(df[feature_x], df[feature_y], c=df['cluster'])
        plt.xlabel(feature_x)
        plt.ylabel(feature_y)
        plt.title(f'KMeans Clustering with {n_clusters} Clusters')

        img = io.BytesIO()
        plt.savefig(img, format='png')
        img.seek(0)
        kmeans_plot = base64.b64encode(img.getvalue()).decode('utf-8')
        plt.close()

        return jsonify([{
            'kmeans_plot': kmeans_plot
        }])

# THE GRAPH FUNCTION, gets 5 
@app.route("/api/graph")
def the_graph():
    swaps_df = the_graph_access()
    swaps_df = swaps_df.astype({"amount0":float, "amount1":float, "amountUSD":float, "timestamp":int})

    # return jsonify(swaps_df.query('amountUSD > 0').to_dict())
    return jsonify(swaps_df.query(request.args.get('query')).to_dict())
    # return swaps_df.to_dict()

def the_graph_access():
    
    # Create a transport instance
    transport = AIOHTTPTransport(
        url="https://gateway-arbitrum.network.thegraph.com/api/c6e4f87e7381de5513ae5ecfa70df065/subgraphs/id/5zvR82QoaXYFyDEKLZ9t6v9adgnptxYpKpSbxtgVENFV",
        timeout=30,  # Increase the timeout value if needed
    )

    # Create a client instance
    client = Client(
        transport=transport,
        fetch_schema_from_transport=True,
    )

    # Define the GraphQL query
    query = gql(
        """
        query {
            pools(first: 10, orderBy: volumeUSD, orderDirection: desc) {
                id
                token0 {
                    id
                    symbol
                    name
                    decimals
                }
                token1 {
                    id
                    symbol
                    name
                    decimals
                }
                feeTier
                liquidity
                sqrtPrice
                tick
                volumeUSD
                volumeToken0
                volumeToken1
                txCount
            }
            tokens(first: 10, orderBy: volumeUSD, orderDirection: desc) {
                id
                symbol
                name
                decimals
                volume
                volumeUSD
                txCount
                whitelistPools {
                    id
                }
            }
            swaps(first: 10, orderBy: timestamp, orderDirection: desc) {
                id
                timestamp
                pool {
                    id
                }
                token0 {
                    id
                    symbol
                }
                token1 {
                    id
                    symbol
                }
                sender
                recipient
                amount0
                amount1
                amountUSD
            }
        }
        """
    )

    # Execute the query
    result = client.execute(query)
    # print(result)
    # create a pandas dataframe from the result
    swaps_df = pd.DataFrame(result["swaps"], )
    # print the first 5 latest swaps of uniswap v3
    return swaps_df


@app.route("/api/vis")
def vis():
    return ""

if __name__ == '__main__':
    app.run(debug=True, host = '0.0.0.0', port = 3005)

