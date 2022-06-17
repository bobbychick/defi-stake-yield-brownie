from brownie import network, exceptions
from scripts.helpful_scripts import (
    DECIMALS,
    INITIAL_PRICE_FEED_VALUE,
    LOCAL_BLOCKCHAIN_ENVIRONMENTS,
    get_account,
    get_contract,
)
import pytest
from scripts.deploy import deploy_token_farm_and_dapp_token, KEPT_BALANCE
from web3 import Web3


def test_set_price_feed_contract():
    # Arrange
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing!")

    account = get_account()
    non_owner = get_account(index=1)
    token_farm, dapp_token = deploy_token_farm_and_dapp_token()

    # Act
    price_feed_address = get_contract("eth_usd_price_feed")
    token_farm.setPriceFeedContract(
        dapp_token.address, price_feed_address, {"from": account}
    )
    # Assert
    assert token_farm.tokenPriceFeedMapping(dapp_token.address) == price_feed_address
    with pytest.raises(exceptions.VirtualMachineError):
        token_farm.setPriceFeedContract(
            dapp_token.address, price_feed_address, {"from": non_owner}
        )


def test_stake_tokens(amount_staked):
    # Arrange
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing!")
    account = get_account()
    token_farm, dapp_token = deploy_token_farm_and_dapp_token()
    # Act
    dapp_token.approve(token_farm.address, amount_staked, {"from": account})
    token_farm.stakeTokens(amount_staked, dapp_token.address, {"from": account})
    # Assert
    assert (
        # stakingBalance is a mapping of a mapping, need to pass 2 address using below syntax
        token_farm.stakingBalance(dapp_token.address, account.address)
        == amount_staked
    )
    # correctly stakes 1 token
    assert token_farm.uniqueTokensStaked(account.address) == 1
    # the first staker is our account
    assert token_farm.stakers(0) == account.address
    return token_farm, dapp_token


def test_issue_tokens(amount_staked):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing!")
    account = get_account()
    token_farm, dapp_token = test_stake_tokens(amount_staked)
    starting_balance = dapp_token.balanceOf(account.address)
    # Act
    token_farm.issueTokens({"from": account})
    # Assert
    # we are staking 1 dapp_token == in price to 1 ETH
    # so we should get 2,000 dapp tokens in reward, since price of eth is $2,000 usd
    assert (
        dapp_token.balanceOf(account.address)
        == starting_balance + INITIAL_PRICE_FEED_VALUE
    )


def test_get_user_single_token_value(amount_staked):
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing!")
    account = get_account()
    token_farm, dapp_token = test_stake_tokens(amount_staked)
    # Value of dapp_token
    dappSingleTokenValue = token_farm.getUserSingleTokenValue(account, dapp_token)
    # Assert: single token value of dapp is equal to balance of dapp
    assert dappSingleTokenValue == dapp_token.balanceOf(account.address)


def test_get_user_token_staking_balance_eth_value(amount_staked):
    # Arrange
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing!")
    account = get_account()
    token_farm, dapp_token = deploy_token_farm_and_dapp_token()
    # Act
    dapp_token.approve(token_farm.address, amount_staked, {"from": account})
    token_farm.stakeTokens(amount_staked, dapp_token.address, {"from": account})

    # Assert
    eth_balance_token = token_farm.getUserTokenStakingBalanceEthValue(
        account.address, dapp_token.address
    )
    assert eth_balance_token == Web3.toWei(2000, "ether")


# This may count as an integration test (staking multiple tokens)
def test_get_user_total_value(amount_staked):
    # Arrange: get account and only test if on development
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing!")
    account = get_account()
    # Act: stake dapp_tokens
    token_farm, dapp_token = test_stake_tokens(amount_staked)
    totalValue = token_farm.getUserTotalValue(account)
    # Assert: total value should be equal to value of dapp_token

    assert totalValue == dapp_token.balanceOf(account.address)


def test_get_user_total_balance_with_different_tokens_and_amounts(
    amount_staked, random_erc20
):
    # Arrange
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")
    account = get_account()
    token_farm, dapp_token = test_stake_tokens(amount_staked)
    # Act
    token_farm.addAllowedTokens(random_erc20.address, {"from": account})
    # The random_erc20 is going to represent DAI
    # Since the other mocks auto deploy
    token_farm.setPriceFeedContract(
        random_erc20.address, get_contract("eth_usd_price_feed"), {"from": account}
    )
    random_erc20_stake_amount = amount_staked * 2
    random_erc20.approve(
        token_farm.address, random_erc20_stake_amount, {"from": account}
    )
    token_farm.stakeTokens(
        random_erc20_stake_amount, random_erc20.address, {"from": account}
    )
    # Act
    total_eth_balance = token_farm.getUserTotalValue(account.address)
    assert total_eth_balance == INITIAL_PRICE_FEED_VALUE * 3
    # Improve by adding different mock price feed default values


def test_get_token_eth_price():
    # Arrange
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")
    token_farm, dapp_token = deploy_token_farm_and_dapp_token()
    # Act / Assert
    assert token_farm.getTokenEthPrice(dapp_token.address) == (
        INITIAL_PRICE_FEED_VALUE,
        DECIMALS,
    )


def test_unstake_tokens(amount_staked):
    # Arrange: get account and only test if on development
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing!")
    account = get_account()
    # Act: stake dapp_tokens
    token_farm, dapp_token = test_stake_tokens(amount_staked)
    token_farm.unstakeTokens(dapp_token.address, {"from": account})
    assert token_farm.balanceOf(account.address) == KEPT_BALANCE
    assert token_farm.stakingBalance(dapp_token.address, account.address) == 0
    assert token_farm.uniqueTokensStaked(account.address) == 0


def test_update_unique_tokens_staked(amount_staked):
    # Arrange: get account and only test if on development
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing!")
    account = get_account()
    # Arrange: get token_farm & dapp_token contract
    token_farm, dapp_token = test_stake_tokens(amount_staked)
    weth_token = get_contract("weth_token")
    # token_farm.updateUniqueTokensStaked(account.address, weth_token)
    # Assert: unique tokens staked == 1 ** This isn't an actual test yet, need to figure out
    # How to implement above line
    assert token_farm.uniqueTokensStaked(account.address) == 1


def test_add_allowed_tokens():
    # Arrange
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing!")

    account = get_account()
    non_owner = get_account(index=1)
    token_farm, dapp_token = deploy_token_farm_and_dapp_token()
    # act
    token_farm.addAllowedTokens(dapp_token.address, {"from": account})
    # Assert
    assert token_farm.allowedTokens(0) == dapp_token.address
    with pytest.raises(exceptions.VirtualMachineError):
        token_farm.addAllowedTokens(dapp_token.address, {"from": non_owner})


def test_token_is_allowed():
    # Arrange
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing!")

    account = get_account()
    token_farm, dapp_token = deploy_token_farm_and_dapp_token()

    # Act
    test_add_allowed_tokens()
    ans = token_farm.tokenIsAllowed(dapp_token, {"from": account})

    # Assert
    assert ans is True
